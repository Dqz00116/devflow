---
id: ISSUE-devflow-approve-001
title: "devflow approve" crashes when approved_items contains string representation of list
component: devflow CLI
severity: medium
status: open
discovered: 2026-04-24
---

## Summary

`devflow approve ITEM` crashes with `AttributeError: 'str' object has no attribute 'append'` when the `approved_items` state variable is stored as a string `"[]"` instead of a TOML array.

## Reproduction

```bash
devflow set approved_items "[]"    # stores as string, not empty list
devflow approve CODE-REVIEW-xxx    # crashes
```

## Root Cause (2 bugs)

### Bug 1: `cli.py:533` — `set` command coerces all values to string

```python
@click.argument("value")
def set(key: str, value: str) -> None:
    ...
    state.set("approved_items", "[]")  # value is literally the string "[]"
```

The `set` CLI command declares `value: str`, so Click passes the argument as-is. `"[]"` is written to state.toml as a TOML string:

```toml
approved_items = "[]"    # ← TOML string, not array
```

When the intention was:

```toml
approved_items = []      # ← TOML empty array
```

### Bug 2: `cli.py:523` — `StateStore.get()` default never activates

```python
approved_items = state.get("approved_items", [])
```

The default `[]` only applies when the key is **absent** from state.toml. Since `approved_items = "[]"` exists as a string value, `get()` returns the string `"[]"`. `.append()` then fails.

## Impact

- Blocks advancement past the `code-review` step in MODE-A (gate = `user_approved:CODE-REVIEW-xxx`)
- User must manually edit state.toml to replace string `"[]"` with array `[]`
- Any workflow step using `user_approved` gate is affected

## Fix Proposal

### Short-term (state.toml workaround)

Manually edit `.devflow/state.toml`:

```diff
- approved_items = "[]"
+ approved_items = []
```

### Medium-term (CLI fix — preferred)

Two changes in `cli.py`:

**1. `set` command — add type coercion** (cli.py ~533):

```python
def _coerce_value(raw: str) -> Any:
    """Coerce string to appropriate Python type."""
    stripped = raw.strip()
    if stripped == "[]":
        return []
    if stripped == "{}":
        return {}
    if stripped in ("true", "false"):
        return stripped == "true"
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass
    return raw

@cli.command()
@click.argument("value")
def set(key: str, value: str) -> None:
    state = StateStore.from_project()
    coerced = _coerce_value(value)
    state.set(key, coerced)
```

**2. `approve` command — defensive type guard** (cli.py ~523):

```python
approved_items = state.get("approved_items", [])
if not isinstance(approved_items, list):
    approved_items = []  # recover from malformed state
```

### Long-term (architecture)

- `StateStore.set()` should validate known list-type keys (`approved_items`, `step_history`) and warn on type mismatch
- Add `devflow reset-approved` subcommand to clear approved items atomically

## Affected Files

| File | Line(s) | Role |
|------|---------|------|
| `devflow/cli.py` | 523, 525, 533 | `approve` and `set` commands |
| `devflow/state_store.py` | 40-43 | `set()` writes without type checks |
| `devflow/state_store.py` | 36-38 | `get()` returns raw TOML value |
