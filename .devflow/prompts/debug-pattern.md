## Phase 2: Pattern Analysis

Find working examples and identify patterns.

### Output File:
docs/debug/PATTERN-{workflow_run_id}.md

### Tasks:
1. Find working examples:
   - Similar functionality that works
   - Previous versions that worked
   - Similar patterns in codebase

2. Read reference implementation COMPLETELY:
   - Understand how it handles similar cases
   - Note ALL differences

3. Create pattern document:

   ## Working Example
   File: [path]
   ```
   [relevant code]
   ```

   ## Current (Broken) Code
   File: [path]
   ```
   [relevant code]
   ```

   ## Differences
   | Aspect | Working | Broken |
   |--------|---------|--------|
   | X | value1 | value2 |
   | Y | ... | ... |

4. Identify dependencies:
   - What does the broken code depend on?
   - What has changed in dependencies?

### Gate:
- PATTERN-{workflow_run_id}.md created
