# Root Cause Analysis: `devflow init` produces empty `.devflow/prompts/`

**Bug ID:** 90e89929

**Date:** 2026-06-27

**Severity:** Medium -- workflows render without prompt content, making `devflow current` useless for new projects.

## Bug

`devflow init` produces an empty `.devflow/prompts/` directory. Workflows reference `mode-a/` and `mode-b/` prompt files but none exist, so `load_prompt()` returns empty strings and steps render with no prompt content.

## Reproduction

1. `cd /path/to/project && devflow init`
2. `ls .devflow/prompts/` -- empty, no `mode-a/` or `mode-b/` subdirectories
3. `devflow current` -- shows empty prompt (no content)

## Root Cause

**File:** `src/devflow/template.py`, function `init_project_templates()`

**Commit that introduced the bug:** `2b7364e` ("feat(init): use repository .devflow/ as the template for devflow init")

The original code at lines 170-171:

```python
for md_file in prompts_dir.glob("*.md"):
    dest_path = project_root / ".devflow" / "prompts" / md_file.name
```

Two problems:

1. **Non-recursive glob (line 170):** `prompts_dir.glob("*.md")` only matches `.md` files directly inside `prompts_dir`. After the v3.0 restructuring that placed prompts into `mode-a/` and `mode-b/` subdirectories, no flat `.md` files remain at the root level. The glob returns zero results, and nothing gets copied.

2. **Flattened destination (line 171):** `md_file.name` strips the subdirectory prefix. Even if `rglob("*.md")` were used, `mode-a/req-create.md` would be incorrectly flattened to `req-create.md`, landing at `.devflow/prompts/req-create.md` instead of `.devflow/prompts/mode-a/req-create.md`.

## Evidence

- `src/devflow/data/prompts/` has only `mode-a/` and `mode-b/` subdirectories -- zero flat `.md` files:
  - `mode-a/brainstorm.md`, `mode-a/req-create.md`, `mode-a/req-approve.md`, `mode-a/write-plan.md`, `mode-a/implement-verify.md`, `mode-a/finish.md`
  - `mode-b/debug-root-cause.md`, `mode-b/debug-pattern.md`, `mode-b/debug-hypothesis.md`, `mode-b/debug-fix.md`, `mode-b/debug-question.md`, `mode-b/debug-verify.md`, `mode-b/debug-finish.md`
- `D:\project_tower\.devflow\prompts\` confirmed empty after running `devflow init`
- `load_prompt()` resolves paths like `mode-a/req-create.md` correctly against `.devflow/prompts/` but the file does not exist, so it returns an empty string

## Fix Applied

Two-line change in `src/devflow/template.py`:

- **Line 170:** `glob("*.md")` changed to `rglob("*.md")` (recursive search into subdirectories)
- **Line 171:** `md_file.name` changed to `md_file.relative_to(prompts_dir)` (preserves subdirectory structure in the destination path)

### Before

```python
for md_file in prompts_dir.glob("*.md"):
    dest_path = project_root / ".devflow" / "prompts" / md_file.name
```

### After

```python
for md_file in prompts_dir.rglob("*.md"):
    dest_path = project_root / ".devflow" / "prompts" / md_file.relative_to(prompts_dir)
```

### Verification

- All 154 tests pass after the fix.
- `devflow init` now correctly copies `mode-a/*.md` and `mode-b/*.md` into `.devflow/prompts/` with their subdirectory structure preserved.

## Status

- **Fix Applied:** Yes (working tree, not yet committed)
- **Branch:** main (working tree changes)
