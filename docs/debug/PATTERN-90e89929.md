# Pattern Analysis: Fragile Flat Globs

**Bug ID:** 90e89929

**Date:** 2026-06-27

## Comparison Dimensions

1. Working: Workflow copy (`template.py:162`, `glob("*.toml")`) — flat files, no subdirectories
2. Broken: Prompt copy (`template.py:170`, was `glob("*.md")`) — subdirectories `mode-a/` `mode-b/`

## Working vs Broken

| Aspect | Working (workflow copy) | Broken (prompt copy) |
|---|---|---|
| File structure | Flat `.toml` files | Subdirectories `mode-a/` `mode-b/` with `.md` |
| Glob | `glob("*.toml")` | `glob("*.md")` (was) |
| Finds files? | Yes — all at top level | No — zero flat files |
| Destination path | `md_file.name` only | `md_file.name` (was, would flatten) |
| Fixed? | N/A | `rglob` + `relative_to` |

## Codebase-wide Pattern Audit

All `glob()` calls in `src/devflow/`:

| File | Line | Call | Safety |
|---|---|---|---|
| `template.py` | 162 | `glob("*.toml")` | SAFE — flat workflows, no subdirs |
| `template.py` | 170 | `rglob("*.md")` | FIXED — was `glob`, now recursive |
| `cli.py` | 378 | `glob("*.toml")` | SAFE — flat workflows |
| `workflow_parser.py` | 249 | `glob("*.toml")` | SAFE — flat workflows |
| `feat_cmd.py` | 122 | `glob("FEAT-*.md")` | SAFE — flat docs dirs |
| `req_cmd.py` | 109 | `glob("REQ-*.md")` | SAFE — flat docs dirs |
| `status_cmd.py` | 46,55 | `glob("REQ-*.md")`, `glob("FEAT-*.md")` | SAFE — flat docs dirs |
| `gate_checker.py` | 64,110 | `glob(pattern)` | FOOTGUN — user-provided `*.py` matches only top-level |
| `vcs.py` | 110 | `glob(pattern)` | SAFE — user-provided, but typically `*.py` or `**/*` |

## Identified Pattern

**Fragile flat globs — code assumes single-level file organization but data has been reorganized into subdirectories.**

The root cause follows a classic pattern: data structure changed (flat `*.md` at root became nested in `mode-a/` `mode-b/`), copy logic didn't adapt. The workflow copy still works only because workflows haven't been reorganized into subdirectories. If workflows ever get subdirectories, the same bug will recur on `template.py:162`.

This pattern has two complementary failure modes:

1. **Non-recursive discovery:** `glob("*.ext")` returns zero results when files move into subdirectories, leading to silent empty copies or missing file lists.
2. **Flattening:** `md_file.name` strips subdirectory context, so even if files are found they land in the wrong location.

## Implications for Future Code

- **Use `rglob` + `relative_to` for recursive copy operations.** Anytime you copy or iterate a tree of files, prefer recursive traversal and path-preserving destinations unless you are certain the data will always remain flat.
- **Document `gate_checker.py` pattern gates.** The `file_exists_pattern` and `file_contains_pattern` gates accept a user-supplied glob. If a user writes `*.py` instead of `**/*.py`, they will miss deep files. The documentation should recommend `**/` prefix for recursive matching.
- **Preventive: switch `template.py:162` to `rglob`** for workflow copying too. Even though workflows are flat today, this makes the code robust against future nested organization.
- **Test for structural assumptions.** If test data includes subdirectories but the code under test only uses flat globs, the tests may pass for the wrong reasons. Add at least one test case where the source tree has nested files.
