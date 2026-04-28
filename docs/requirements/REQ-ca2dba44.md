---
id: REQ-ca2dba44
title: Fix implement-sdd.md to enforce SDD subagent dispatch
status: done
priority: high
---

## Description

MODE-A 的 `implement-sdd.md` 提示词实际执行时，AI 主 Agent 会跳过"派发子 Agent"步骤，直接自己走 TDD（RED-GREEN-REFACTOR），违背了 SDD（Subagent-Driven Development）的设计意图。

根因：提示词结构将 SDD 流程和 TDD 细节混在一起，AI 看到熟悉的 TDD 模式后直接执行，把子 Agent 派发视为可选的实现细节。Iron Law 只约束 TDD，未约束 SDD。Gate 只验证测试通过，不验证是否使用了子 Agent。

需要重构提示词，将子 Agent 派发变为不可跳过的强制步骤。

## Acceptance Criteria

- [ ] 主 Agent 阅读 implement-sdd 提示词后，必须先派发子 Agent 执行实现
- [ ] TDD 循环细节移入子 Agent 的上下文中，不出现在主 Agent 指令里
- [ ] 主 Agent 的职责明确为：派发、审核（spec 合规优先）、合并
- [ ] 增加 SDD Iron Law：主 Agent 禁止直接编写生产代码
- [ ] Gate 仍然只检查测试通过（`command_success:{test_command}`）

## Notes

- 同时更新 `src/devflow/data/prompts/implement-sdd.md`（打包版本），保持与 `.devflow/prompts/implement-sdd.md` 一致
- 不改变 MODE-A.toml 的步骤结构
