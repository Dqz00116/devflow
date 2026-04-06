# Requirements Management

This document describes how to manage requirements in this project.

## Requirement States

Requirements follow this state machine:

```
DRAFT → ANALYZING → ANALYZED → APPROVED → IN_PROGRESS → DONE
```

| State | Description |
|-------|-------------|
| **DRAFT** | Initial creation, basic idea captured |
| **ANALYZING** | Under analysis, design options being explored |
| **ANALYZED** | Analysis complete, design documented |
| **APPROVED** | Approved for implementation |
| **IN_PROGRESS** | Currently being implemented |
| **DONE** | Implementation complete |

## Creating Requirements

### Using CLI

```bash
# Create a new requirement
devflow req new REQ-001 --title "User Authentication"

# Edit the generated file
docs/requirements/REQ-001.md

# Update status
devflow req status REQ-001 analyzing
```

### File Format

Requirements are stored as Markdown files in `docs/requirements/`:

```markdown
---
id: REQ-001
title: User Authentication
status: draft
priority: high
created: 2024-01-15
---

## Description
Implement user authentication system...

## Acceptance Criteria
- [ ] Users can register with email
- [ ] Users can login with email/password
- [ ] Passwords are securely hashed

## Design Document
- Design: `docs/superpowers/specs/2024-01-15-auth-design.md`

## Tasks
- TASK-001: Setup auth middleware
- TASK-002: Implement login endpoint

## Notes
Additional context...
```

## Priority Levels

| Level | Use When |
|-------|----------|
| **critical** | Blocks release, fix immediately |
| **high** | Important feature, do soon |
| **medium** | Normal priority |
| **low** | Nice to have, do when time permits |

## Requirement IDs

Format: `REQ-NNN` (e.g., REQ-001, REQ-002)

- Sequential numbers
- Never reuse IDs
- Reference in commits: "Implement REQ-001: User auth"

## Workflow Integration

```
User Request
    ↓
Create REQ-XXX (status: draft)
    ↓
Stage 1: Brainstorming → Update REQ with design
    ↓
Status: approved
    ↓
Create FEAT-XXX for technical implementation
    ↓
FEAT Status: implemented (implementation complete)
    ↓
Create TASK-XXX for tracking work
    ↓
All TASKs done
    ↓
REQ Status: done
```

**Key Points**:
- **REQ** captures the business requirement and design
- **FEAT** documents the technical implementation (required before marking REQ done)
- **TASK** tracks actual work items during implementation
- REQ can only be marked **done** after FEAT is **implemented**

## Listing Requirements

```bash
# List all requirements
devflow req list

# Filter by status
devflow req list --status approved

# Show details
devflow req show REQ-001
```

## Best Practices

1. **One requirement per feature** - Don't bundle unrelated features
2. **Clear acceptance criteria** - Define "done" upfront
3. **Link design docs** - Reference specs in the requirement
4. **Create FEAT after REQ approved** - Technical implementation must be documented
5. **FEAT must be implemented before REQ done** - FEAT is the implementation record
6. **Update status promptly** - Keep status accurate
7. **Archive done requirements** - Keep as record, don't delete

## Feature (FEAT) vs Requirement (REQ)

| Aspect | REQ | FEAT |
|--------|-----|------|
| **Purpose** | Business requirement | Technical implementation |
| **Created when** | After idea capture | After REQ approved |
| **Contains** | What & Why | How (code, architecture) |
| **Required for** | Planning & tracking | Implementation record |
| **Must complete before** | Design approval | REQ can be marked done |

---

See also:
- [WORKFLOW.md](WORKFLOW.md) - Complete development workflow
- [AGENTS.md](../AGENTS.md) - Project context
- [features/TEMPLATE.md](features/TEMPLATE.md) - Feature template
- [requirements/TEMPLATE.md](requirements/TEMPLATE.md) - Requirement template
