## Create Requirement

Create the requirement document.

### Tasks:
1. Create file: docs/requirements/REQ-{workflow_run_id}.md

2. Fill in frontmatter:
   ```yaml
   ---
   id: REQ-{workflow_run_id}
   title: [Feature Name]
   status: draft
   priority: [low/medium/high/critical]
   ---
   ```

3. Write sections:
   ## Description
   [What problem this solves, who is the user]

   ## Acceptance Criteria
   - [ ] Specific, verifiable criterion 1
   - [ ] Specific, verifiable criterion 2

   ## Notes
   [Additional context, constraints]

### Tips:
- Focus on "WHAT" not "HOW"
- Acceptance criteria must be testable
- One requirement per feature

### Gate:
- REQ-{workflow_run_id}.md created
