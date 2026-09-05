---
id: spec-20260906-harness-execution
level: L1
summary: 干净快照前检、无认证局部诊断与精确隔离执行
load_when:
  - task:20260906-harness-execution
author: Codex
task_id: 20260906-harness-execution
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/workflows/verify.md
  - harness/docs/decisions/20260906-harness-execution.md
documentation_reason: 明确快照检查、初始化、诊断资格、身份核验与批次隔离的运行合同
state_history:
---

# Context

用户于 2026-09-06 要求实施 workflow-friction_confirmed 提案。A–C 优先实施；D 独立评审，复用保持关闭。当前工作区的 UI 审计报告和提案材料属于既有修改，不能覆盖。

# Goal

在不缩小完整任务影响范围的前提下，把快照缺陷和初始化失败前置，提供不授予认证的精确局部诊断，并以完整测试身份和显式数据策略控制批次执行。只有同条件成本证据达标才默认开放合并策略。

# Non-goals

不改产品页面、业务 API、部署、AGENTS.md 或历史证据；不启用跨提交认证复用，不自动安装依赖。

# Acceptance criteria

- AC-1: 固定 HEAD 快照检查先于依赖链接、初始化与产品执行，失败时消费者不执行；同快照结果承担 integrity gate。
- AC-2: 所选配置显式声明初始化合同，每隔离上下文只执行一次；失败保存阶段与精确消费者，Harness-only 不启动 Node。
- AC-3: diagnose 按当前 case 或可信失败子集隔离执行，不覆盖正式证据、账本 aggregate 或关闭资格；不确定引用阻断。
- AC-4: 精确身份包含 config/project/path/title_path，收集与执行拒绝重复、遗漏、扩张、跳过、重试和同数不同身份；数据未声明或独占时每身份独立 runtime。
- AC-5: 批次产物独立保留，阶段失败有来源且后续消费者 not-run；输入漂移及清理失败继续阻断认证。批量执行默认关闭，须通过对称配对成本测量后才能启用。

# Risks

Playwright 文本选择具有前缀语义，必须以集合证明拦截。旧引用只能唯一解析。共享数据库的测试必须逐项证明 fixture 隔离，不能以重启服务代替清理。真实性能测量成本独立披露，未达门槛不能宣称性能完成。

# Verification plan

## Verification cases

- AC-1 => M08-SNAPSHOT-01
- AC-2 => M08-PREREQUISITE-01, M08-IMPACT-PREREQUISITES-01
- AC-3 => M08-DIAGNOSE-01, M08-IMPACT-REPORTING-01
- AC-4 => M08-EXACT-IDENTITY-01, M08-COLLECTOR-01, M08-IMPACT-GRAPH-01, M08-IMPACT-MAPPING-01, M08-IMPACT-RUNNERS-01, M08-IMPACT-SELECTION-01, M08-IMPACT-SELECTION-02, M08-IMPACT-SELECTION-03, M08-SEMANTICS-01, M08-TRACE-01, M08-TRACE-02, M08-TRACE-03, M08-TRACE-04
- AC-5 => M08-BATCH-ARTIFACTS-01, M08-DOCS-01, M08-EVIDENCE-01, M08-IMPACT-BENCHMARK-01, M08-IMPACT-CLOSURE-01, M08-IMPACT-CLOSURE-03, M08-IMPACT-EXECUTION-01, M08-IMPACT-EXECUTION-02, M08-IMPACT-EXECUTION-03, M08-IMPACT-EXECUTION-04, M08-RESUME-01, M08-RESUME-02, M08-RESUME-03, M08-RESUME-04, M08-SPEC-01, M08-VALIDATOR-01

## Gates

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5
