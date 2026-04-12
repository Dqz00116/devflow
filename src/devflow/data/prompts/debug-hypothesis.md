## Phase 3: Hypothesis & Testing

Form a single, testable hypothesis.

### Output File:
docs/debug/HYPOTHESIS-{workflow_run_id}.md

### Tasks:
1. Form hypothesis:
   "[X] is the root cause because [Y]"

   Example:
   "The null pointer occurs because the config
    is not loaded before the service starts"

2. Create hypothesis document:

   ## Hypothesis
   [Single, specific statement]

   ## Reasoning
   [Why you think this is the cause]

   ## Test Plan
   [How to verify with minimal change]

3. Test minimally:
   - Change ONE variable
   - Keep everything else constant
   - Verify: Works → proceed to fix
   - Verify: Fails → new hypothesis

4. Document test results:
   ## Test Results
   Test: [what was changed]
   Result: [success/failure]
   Conclusion: [validated/invalidated hypothesis]

5. Iterate if needed:
   - Hypothesis fails? Form new one
   - Max 3 attempts before questioning approach

### Gate:
- HYPOTHESIS-{workflow_run_id}.md created
- Hypothesis validated
