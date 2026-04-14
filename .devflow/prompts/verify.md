## Stage 6: Verification

Verify implementation meets acceptance criteria with concrete evidence.

### Output File:
docs/evidence/EVIDENCE-{workflow_run_id}.md

### Skill:
`verification-before-completion`

### Process (IDENTIFY → RUN → READ → VERIFY → CLAIM):
1. **IDENTIFY**: What command proves this criterion?
2. **RUN**: Execute FULL command fresh
3. **READ**: Read full output, check exit code
4. **VERIFY**: Does output confirm success?
5. **CLAIM**: Document with evidence

### For each acceptance criterion:
```
## Criterion 1: [Description]
**Command:** `pytest tests/test_feature.py::test_criterion`
**Output:**
```
[paste full output]
```
**Result:** PASSED / FAILED
```

### Forbidden phrases:
- "Should work"
- "Probably passes"
- "Seems correct"

**Required**: Concrete evidence!

### Gate:
- EVIDENCE-{workflow_run_id}.md created
- All criteria verified
