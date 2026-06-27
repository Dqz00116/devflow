# Debug Completion - 90e89929

## Bug
`devflow init` produces empty `.devflow/prompts/` directory — no prompt files are copied to target projects.

## Debug Summary

### Root Cause
`src/devflow/template.py` line 170 uses non-recursive `glob("*.md")` which returns zero results when all .md files are in `mode-a/` and `mode-b/` subdirectories (v3.0 restructure). Line 171 `md_file.name` also strips subdirectory paths, causing filename collisions.

### Pattern Identified
Fragile flat globs: code assumes single-level file organization but data was reorganized into subdirectories. The v3.0 prompt restructure changed flat `.md` files to `mode-a/` and `mode-b/` subdirectories without updating the copy logic. Three other `glob("*.toml")` sites remain safe only because workflows are still flat.

### Fix Applied
Two-line change in `src/devflow/template.py`:
- Line 170: `glob("*.md")` → `rglob("*.md")` (recursive matching)
- Line 171: `md_file.name` → `md_file.relative_to(prompts_dir)` (preserve subdirectory structure)

### Verification
Full test suite: 154 passed. Zero regressions. Fix verified working.

## Artifacts
| Document | Path |
|----------|------|
| Root Cause Investigation | docs/debug/ROOT-CAUSE-90e89929.md |
| Pattern Analysis | docs/debug/PATTERN-90e89929.md |
| Hypothesis & Fix | docs/debug/HYPOTHESIS-90e89929.md |
| Verification Report | docs/debug/VERIFICATION-90e89929.md |

## Next Steps
Transitioning to MODE-A:write-plan for implementation planning.
