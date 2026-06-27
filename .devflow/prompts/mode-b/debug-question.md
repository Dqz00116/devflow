# Debug Phase 4.5: Question Architecture (Human Required)

## Role

| Role | Responsibilities |
|------|-----------------|
| **Main Agent** | Present findings to user, articulate architectural dilemma, ask three key questions, record decision. |
| **Subagent(s)** | Summarize all debug findings for presentation. |

Main agent designs & reviews. ALL operational work (file I/O, commands, search) MUST be dispatched to subagents.

## Execution Model

```
Subagent summarizes all debug findings
  |-- Main Agent presents to user with structured questions
  |-- User decides: Refactor / Fix differently / Abandon / Continue more investigation
  |     User runs: devflow approve ARCHITECTURE-REVIEW-{workflow_run_id}
  |     User runs: devflow done
  |       --> Step succeeds --> next = debug-root-cause (re-investigate with guidance)
```

## Input

- `docs/debug/ROOT-CAUSE-{workflow_run_id}.md`
- `docs/debug/PATTERN-{workflow_run_id}.md`
- `docs/debug/HYPOTHESIS-{workflow_run_id}.md` (with failed attempts + failure count)
- All previous debug documents from this run

## Output

- User decision (no new output document — user approval is the gate)

## Gate

- `user_approved:ARCHITECTURE-REVIEW-{workflow_run_id}`

## Procedure

- **Subagent: Summarize findings**: Dispatch subagent to compile concise summary:
  ```markdown
  ## Debug Summary -- {workflow_run_id}
  Root Cause, Pattern Analysis, Hypothesis Tested, Fix Attempts, Current State
  ```
- **Main Agent: Present to user** — ask these three questions explicitly:
  1. **Pattern question**: "Is the pattern fundamentally sound, or tracing the wrong thread?"
  2. **Inertia question**: "Are we continuing from inertia after too many attempts in a wrong direction?"
  3. **Approach question**: "Refactor surrounding architecture, fix the symptom, or abandon approach?"
- **User decision**: User reads summary + questions, runs `devflow approve ARCHITECTURE-REVIEW-{workflow_run_id}`, then `devflow done`.
- **After approval**: Workflow advances to `next = "debug-root-cause"` for re-investigation with user's guidance and accumulated context.

## Completion Criteria

- User presented with structured summary of all debug findings
- Three architectural questions asked explicitly
- User confirmed decision via `devflow approve`
- Step advances to re-investigation with user's guidance
