## Phase 1: Root Cause Investigation

Before fixing, understand WHAT and WHY.

### Output File:
docs/debug/ROOT-CAUSE-{workflow_run_id}.md

### Skill:
`systematic-debugging`

### Tasks:
1. Read `systematic-debugging` skill

2. Create root cause document

3. Gather evidence:
   ## Error Information
   - Error message: [exact text]
   - Stack trace: [key lines]
   - Line numbers: [specific locations]

   ## Reproduction
   - Steps to reproduce: [numbered list]
   - Frequency: [always/sometimes/rare]
   - Environment: [local/staging/production]

4. Recent changes:
   ```bash
   git log --oneline -10
   git diff HEAD~1
   ```

5. Gather evidence at boundaries:
   - Input data at failure point
   - Output data at failure point
   - Component boundaries

6. Trace data flow:
   - Where does data come from?
   - Where does it go?
   - Where does it become wrong?

### Completion Criteria:
- Can consistently reproduce the issue
- Understand exactly WHAT is failing
- Understand WHY it's failing (root cause)

### Gate:
- ROOT-CAUSE-{workflow_run_id}.md created
