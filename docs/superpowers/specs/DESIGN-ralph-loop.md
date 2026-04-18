# DevFlow + Ralph Loop Integration Design

## 1. First-Principles Analysis

### 1.1 The First Principles of AI-Assisted Development

The essence of AI-assisted development is not "a more complex command menu" — it is: **continuously and reliably translating human intent into working, correct code**.

This process consists of three irreducible elements:
1. **Intent**: what to do (requirements / tasks)
2. **Validation**: whether it was done correctly (tests / gates)
3. **Memory**: persistence of context and learned patterns

DevFlow already solves "intent structuring" (TOML workflows) and "validation automation" (the gate system) well, but **memory and autonomous progression** still require the agent to manually run `current` -> act -> `done`.

### 1.2 Agent / User First Action

**Problem with the current first action**:
- The agent's first move is `devflow current` to read the prompt
- After making changes, the agent must manually run `devflow done`
- On failure, the agent must read the error and decide the next step

This requires the agent to **stay online and remember to drive the workflow**. The core insight of Ralph Loop is: **make the Loop itself the driver, so the agent only has to execute a single step**.

**Ideal first action**:
- For agents: `devflow run` — start an autonomous loop that runs until the workflow completes or hits a human-in-the-loop blocker
- For users: `devflow plan "implement user login"` — auto-generate a task list and start the loop

---

## 2. Core Ralph Loop Concepts (based on snarktank/ralph)

| Concept | Meaning | DevFlow Mapping |
|---------|---------|-----------------|
| **Fresh Context** | Each iteration spawns a new AI instance | Loop Engine calls `claude`/`amp` as a subprocess |
| **Small Tasks** | Every task must fit in one context window | Workflow steps are inherently small; large requirements split into sub-workflows or backlog items |
| **prd.json** | Machine-readable task list with pass/fail state | `.devflow/backlog.json` or `tasks` in `state.toml` |
| **progress.txt** | Append-only cross-iteration learnings | `.devflow/progress.md` — auto-appends patterns/gotchas |
| **Quality Gates** | Type checks and tests must pass before proceeding | Reuses `gate_checker.py` (`command_success`, etc.) |
| **VCS as Memory** | Every successful iteration is committed | VCS commit/checkpoint becomes the Loop persistence mechanism |

---

## 3. Organic Integration Design

### 3.1 Architecture: Loop is an Automation Layer on top of WorkflowEngine

The design does not break existing responsibilities of `WorkflowEngine`, `StateStore`, or `GateChecker`. Instead it adds a **Loop Engine** (`src/devflow/loop_engine.py`) and a **VCS abstraction layer** (`src/devflow/vcs.py`) above them:

```
┌─────────────────────────────────────┐
│           devflow run               │  ← new entry command
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│         Loop Engine                 │  ← new: scheduling, context cleanup, iteration control
│  ┌─────────┐  ┌─────────┐          │
│  │ Backlog │  │ Progress│          │  ← .devflow/backlog.json + .devflow/progress.md
│  │ Selector│  │ Logger  │          │
│  └────┬────┘  └────┬────┘          │
│       └─────────────┘               │
│              │                      │
│         ┌────┴────┐                 │
│         │ VCS Driver│               │  ← auto-detects Git / SVN / none
│         └────┬────┘                 │
└──────────────┼──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      WorkflowEngine (existing)      │  ← reused: loads steps, checks gates, routes
│      StateStore     (existing)      │  ← reused: persists current step, fail counts
│      GateChecker    (existing)      │  ← reused: defines pass criteria
└─────────────────────────────────────┘
```

### 3.2 New / Extended Modules

#### 3.2.1 `src/devflow/vcs.py` — VCS Abstraction Layer

The Loop must not hard-code `git commit`. It should operate through a VCS driver interface.

```python
from abc import ABC, abstractmethod
from pathlib import Path

class VCSDriver(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def checkpoint(self, message: str) -> bool:
        """Create a checkpoint (Git = commit, SVN = commit)."""
        ...

    @abstractmethod
    def get_last_checkpoint_id(self) -> str | None:
        """Return the latest commit identifier (Git = short SHA, SVN = revision number)."""
        ...

    @abstractmethod
    def has_uncommitted_changes(self) -> bool:
        ...

    @abstractmethod
    def get_diff_summary(self) -> str:
        """Return a summary of changes for progress logging."""
        ...


class GitDriver(VCSDriver):
    def checkpoint(self, message: str) -> bool:
        subprocess.run(["git", "add", "-A"], cwd=self.project_root, check=True)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.project_root,
            capture_output=True,
        )
        return result.returncode == 0

    def get_last_checkpoint_id(self) -> str | None:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    ...


class SVNDriver(VCSDriver):
    def checkpoint(self, message: str) -> bool:
        result = subprocess.run(
            ["svn", "commit", "-m", message],
            cwd=self.project_root,
            capture_output=True,
        )
        return result.returncode == 0

    def get_last_checkpoint_id(self) -> str | None:
        result = subprocess.run(
            ["svn", "info", "--show-item", "revision"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    ...


class NoVCSDriver(VCSDriver):
    """Fallback when no version control system is present."""
    def checkpoint(self, message: str) -> bool:
        # No VCS operation; progress.md is the only memory
        return True

    def get_last_checkpoint_id(self) -> str | None:
        return None

    ...


def detect_vcs(project_root: Path) -> VCSDriver:
    if (project_root / ".git").exists():
        return GitDriver(project_root)
    if (project_root / ".svn").exists():
        return SVNDriver(project_root)
    # Walk upward for SVN working copies (.svn may live in a parent directory)
    for parent in [project_root, *project_root.parents]:
        if (parent / ".svn").exists():
            return SVNDriver(project_root)
    return NoVCSDriver(project_root)
```

**Override via config**: users can also explicitly set VCS in `.devflow/config.toml`:

```toml
[project]
vcs = "svn"   # "git" | "svn" | "none" | "auto" (default)
```

#### 3.2.2 `src/devflow/loop_engine.py`

Core responsibilities of the Loop Engine:
1. **Load Backlog**: read `.devflow/backlog.json` and find the next task with `passes: false`
2. **Map to workflow step**: translate the backlog item into `current_step`
3. **Spawn Agent**: call an external AI tool in a subprocess (see 3.3 Fresh Context)
4. **Auto-validate**: after the agent exits, call `engine.advance()`
5. **Handle results**:
   - **Pass**: call `vcs.checkpoint()`, mark backlog `passes: true`, append learnings to `progress.md`
   - **Fail**: follow fail routes if any; otherwise log the error to `progress.md` and pause the loop for human intervention
6. **Iteration control**: support `max_iterations` and timeouts

```python
class LoopEngine:
    def __init__(self, project_root: Path, tool: str = "claude"):
        self.project_root = project_root
        self.tool = tool  # "claude" | "amp" | "local"
        self.backlog = Backlog.load(project_root)
        self.progress = ProgressLogger(project_root)
        self.vcs = detect_vcs(project_root)

    def run(self, max_iterations: int = 10) -> LoopResult:
        for i in range(max_iterations):
            task = self.backlog.next_pending()
            if not task:
                return LoopResult(status="complete")

            # 1. Map task to workflow step
            engine = self._ensure_workflow_engine(task.workflow_id, task.step_id)

            # 2. Build agent prompt (inject progress.md summary)
            prompt = self._build_agent_prompt(engine, task)

            # 3. Spawn agent
            success, artifact = self._spawn_agent(prompt)

            # 4. Auto-validate (reuses WorkflowEngine.advance)
            adv_success, next_step, msg = engine.advance()

            if adv_success:
                self._checkpoint(task, msg)
            else:
                # Check if a fail route was triggered
                if next_step and next_step.id != task.step_id:
                    self.progress.log(f"Routed on failure: {task.step_id} -> {next_step.id}")
                    continue  # Loop continues with the new step
                else:
                    self.progress.log(f"Blocked at {task.step_id}: {msg}")
                    return LoopResult(status="blocked", step=task.step_id, message=msg)

        return LoopResult(status="max_iterations_reached")

    def _checkpoint(self, task: Task, msg: str) -> None:
        """Persist progress after a step passes, using the VCS abstraction."""
        checkpoint_msg = f"[{task.workflow_id}/{task.step_id}] {task.title}"
        checkpoint_id = None
        if self.vcs.has_uncommitted_changes():
            if self.vcs.checkpoint(checkpoint_msg):
                checkpoint_id = self.vcs.get_last_checkpoint_id()
        self.backlog.mark_done(task.id, checkpoint_id=checkpoint_id)
        self.progress.log(
            f"Completed {task.step_id}. "
            f"Checkpoint: {checkpoint_id or 'no-vcs'}"
        )
```

#### 3.2.3 `src/devflow/backlog.py`

`.devflow/backlog.json` schema:

```json
{
  "source": "MODE-A",
  "tasks": [
    {
      "id": "req-create",
      "workflow_id": "MODE-A",
      "step_id": "req-create",
      "title": "Create Requirement",
      "passes": false,
      "checkpoint_id": null,
      "metadata": { "run_id": "abc123" }
    },
    {
      "id": "implement-tdd",
      "workflow_id": "MODE-A",
      "step_id": "implement-tdd",
      "title": "TDD Implementation",
      "passes": false,
      "checkpoint_id": null,
      "metadata": {}
    }
  ]
}
```

`checkpoint_id` semantics vary by VCS:
- Git → short SHA (e.g. `abc1234`)
- SVN → revision number (e.g. `r4821`)
- No VCS → `null`

The backlog can be **auto-generated** from an existing workflow TOML (one task per step), or created by the user via a `devflow plan` command from natural language.

#### 3.2.4 `src/devflow/progress.py`

`.devflow/progress.md` append-only format:

```markdown
## 2025-04-16 10:23 — implement-tdd
- Pattern: use pytest parametrize to reduce duplication
- Gotcha: when updating `config.py`, remember to sync `tests/test_config.py` fixtures
- Checkpoint: abc1234

## 2025-04-16 10:45 — code-review
- Blocked: user approval required for CODE-REVIEW-abc123
- Action: pause loop and wait for `devflow approve CODE-REVIEW-abc123`
```

Before each Loop iteration, a **summary** of recent progress entries is injected into the agent prompt, enabling cross-iteration memory.

### 3.3 Fresh Context Mechanism

The essence of Ralph Loop is "each iteration is a fresh AI instance". In DevFlow this can be implemented two ways:

**Option A: Subprocess invocation of external CLI (recommended, matches Ralph)**

```python
def _spawn_agent(self, prompt: str) -> tuple[bool, str]:
    if self.tool == "claude":
        # Non-interactive Claude CLI invocation
        result = subprocess.run(
            ["claude", "--print", prompt],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=300,
        )
    elif self.tool == "amp":
        result = subprocess.run(
            ["amp", "--non-interactive", prompt],
            ...
        )
    elif self.tool == "local":
        # In-process execution for testing or CI
        result = subprocess.run(
            [sys.executable, "-m", "devflow.agent_runner", prompt],
            ...
        )
    return result.returncode == 0, result.stdout
```

**Option B: Self-Loop**
If no external CLI is available, the Loop Engine can execute directly in the current Python process, but this sacrifices the clean-context advantage. This serves as a graceful fallback.

### 3.4 Lightweight Workflow TOML Extensions

To optimize workflows for Loop mode, add optional fields:

```toml
[project]
vcs = "auto"                              # "git" | "svn" | "none" | "auto"

[workflow]
id = "MODE-A"
loop_mode = true                          # allow the loop to auto-run this workflow
human_in_the_loop = ["code-review"]       # pause at these steps for human input
auto_checkpoint = true                    # auto-create a VCS checkpoint on pass
```

Step-level controls are also supported:

```toml
[[steps]]
id = "code-review"
name = "Code Review"
prompt = "..."
gates = ["user_approved:CODE-REVIEW-{workflow_run_id}"]
next = "test-run"
loop_behavior = "pause"   # "run" | "pause" | "skip"
```

Behavior:
- `loop_behavior = "run"`: Loop proceeds normally (good for fully automated gates)
- `loop_behavior = "pause"`: Loop pauses at this step for human intervention (e.g. user approval)
- `loop_behavior = "skip"`: Loop skips this step (useful for documentation-only steps during hotfixes)

### 3.5 New CLI Commands

```bash
# Start the autonomous loop (agent first action)
devflow run [--tool claude|amp|local] [--max-iterations 10]

# View loop status and remaining tasks
devflow loop-status

# Generate backlog from the current workflow
devflow sync-backlog

# Reset loop progress (keeps progress.md as history)
devflow loop-reset
```

**`devflow run` execution flow**:

1. Check if `.devflow/backlog.json` exists; if not, auto-generate from the current workflow
2. Auto-detect VCS (Git / SVN / none) or use explicit `config.toml` setting
3. Read `.devflow/progress.md` and extract the last 5 learnings
4. Pick the next pending task and set `current_step`
5. Build prompt:
   ```
   [current step instruction from devflow current]

   [historical learnings from progress.md]

   Your task: complete the current step, then exit. Do not run other commands.
   ```
6. Spawn the agent
7. After the agent exits, run the equivalent of `devflow done` (`engine.advance()`)
8. Update backlog, progress, and VCS checkpoint based on results
9. Repeat 4-8 until complete, blocked, or max_iterations reached

---

## 4. User Experience Paths (First Action Perspective)

### 4.1 Agent Perspective

**Before**:
```
> devflow current        # read prompt
> # write code...
> devflow done           # check gates
> # if failed, read error and fix...
> devflow done
> devflow current        # advance to next step
```

**After**:
```
> devflow run
# Loop takes over; agent receives one clean single-step task at a time
```

The agent's **cognitive load** drops from "remember the entire workflow state" to "just complete the task I was given".

### 4.2 User Perspective

**Before**: the user had to continuously supervise whether the agent was advancing correctly and inspect `devflow done` output.

**After**:
```bash
# Start a feature-dev workflow and let it run (Git project)
$ devflow select-workflow MODE-A
$ devflow run --tool claude

[loop] VCS detected: git
[loop] Starting iteration 1/10
[loop] Task: req-create (MODE-A)
[loop] Agent spawned...
[loop] Gates passed. Checkpoint: abc1234
[loop] Task req-create marked as done.

[loop] Starting iteration 2/10
[loop] Task: req-approve (MODE-A)
...

[loop] Paused at code-review — requires user_approved:CODE-REVIEW-xyz
[loop] Run: devflow approve CODE-REVIEW-xyz
[loop] Then resume with: devflow run
```

For an **SVN project**, output is similar but the checkpoint shows a revision number:
```
[loop] VCS detected: svn
[loop] Gates passed. Checkpoint: r4821
```

For a **project without VCS**, the Loop still works but does not create code checkpoints; change tracking relies entirely on `progress.md`:
```
[loop] VCS detected: none
[loop] Warning: No version control detected. Changes will not be checkpointed.
[loop] Gates passed. Checkpoint: no-vcs
```

The user can **walk away**. The Loop pauses automatically when needed and emits clear resume instructions.

---

## 5. Key Change List

### 5.1 New Files

| File | Responsibility |
|------|----------------|
| `src/devflow/vcs.py` | VCS abstraction layer: auto-detect Git/SVN/none, unified `checkpoint()` API |
| `src/devflow/loop_engine.py` | Loop core: backlog reading, agent spawn, validation, VCS checkpointing |
| `src/devflow/backlog.py` | Read/write `.devflow/backlog.json` and auto-generation |
| `src/devflow/progress.py` | Append and summarize `.devflow/progress.md` |
| `src/devflow/agent_runner.py` | In-process agent wrapper for `--tool local` (optional) |

### 5.2 Modified Files

| File | Change |
|------|--------|
| `src/devflow/cli.py` | Add `run`, `loop-status`, `sync-backlog`, `loop-reset` commands |
| `src/devflow/workflow_parser.py` | Parse new TOML fields: `loop_mode`, `human_in_the_loop`, `loop_behavior` |
| `src/devflow/workflow_engine.py` | No changes to `advance()` etc.; Loop Engine is a caller |
| `src/devflow/state_store.py` | Optional: add loop metadata such as `loop_iteration_count` |
| `src/devflow/config.py` | Add `project.vcs` setting (`"auto"` / `"git"` / `"svn"` / `"none"`) |

### 5.3 New Data Files

| File | Note |
|------|------|
| `.devflow/backlog.json` | Task list (may be gitignored or committed) |
| `.devflow/progress.md` | Append-only learning log (recommended to commit to VCS) |

### 5.4 Backward Compatibility

- **Fully non-breaking**: `devflow current` / `devflow done` remain unchanged
- **Explicit opt-in**: Loop mode is only started via `devflow run`
- **Graceful degradation**:
  - Missing `claude`/`amp` CLI → fallback to `--tool local`
  - No VCS detected → skip checkpointing, continue running with a warning

---

## 6. MVP Proposal

To validate the design quickly, implement in two phases:

### Phase 1: Local Self-Loop (1-2 days)
- Implement `devflow run --tool local`
- Build the VCS abstraction layer (Git + NoVCS first; SVN later)
- Run the Loop Engine in-process with a built-in agent runner
- Validate the backlog -> step -> advance() -> vcs.checkpoint() -> progress loop

### Phase 2: External CLI + SVN (2-3 days)
- Add `--tool claude` and `--tool amp`
- Implement `SVNDriver` (working-copy detection, commit, revision read)
- Implement true fresh-context spawn
- Add `human_in_the_loop` pause behavior
- Improve smart summarization of `progress.md` for prompt injection

---

## 7. Summary

The goal is not to turn DevFlow into another Ralph, but to **graft Ralph Loop's autonomous execution, fresh-context spawning, and append-only learning onto DevFlow's existing workflow engine, gate system, and state store** — while **eliminating hard-coded Git assumptions via a VCS abstraction layer** so the system also works with SVN or no version control at all.

**The single most important change**:
> From "agent manually drives the workflow" to "Loop automatically drives the workflow; the agent only executes a single step".

This dramatically reduces agent cognitive load and lets users truly "start and walk away", intervening only when the Loop explicitly asks for help.
