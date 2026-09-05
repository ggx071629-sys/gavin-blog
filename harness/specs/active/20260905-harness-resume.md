---
id: spec-20260905-harness-resume
level: L1
summary: 以显式影响计划选择模块测试，并验证可信收尾与成本
load_when:
  - task:20260905-harness-resume
author: Gavin
task_id: 20260905-harness-resume
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - harness/docs/decisions/20260905-verification-resume.md
  - harness/workflows/verify.md
documentation_reason: 执行、证据信任边界、失败恢复和关闭职责改变，必须同步耐久决策与操作流程。
state_history:
---

# Context

用户于 2026-09-05 明确要求实施合并后的受影响模块验证提案；此次请求授权具体方案实施。旧 A/B 缓存方案不再主导范围。既有 attempts、失败 evidence 与历史提交保留。

# Goal

测试范围由逐文件影响分析和逐项依赖判断确定。结构检查不调用 collector；规范 runner 执行所选 exact refs。未知归属阻断，普通任务不自动 release。

# Non-goals

不改产品业务代码、AGENTS.md；不构建静态依赖推导系统，不宣称依赖关系清单能证明业务语义完备。未登记产品归属需要先补计划与模块合同。

# Acceptance criteria

- AC-1: 显式源码归属、case 和依赖理由形成独立计划；未知文件与不完整依赖阻断，未影响模块不执行。
- AC-2: runner 使用受限 Pytest/Vitest/Playwright 选择器；结构检查、plan/status、close 不启动产品 collector。fresh 仅执行所选范围。
- AC-3: 默认不复用；仅具备有界输入合同时允许复用。失败后未执行保持 not-run，旧成功不能覆盖新失败，清理失败和中断不能关闭。
- AC-4: 真实 runner 的完整凭据可以被 close 消费；全复用补足隔离来源，同进程 verify --close 不重跑测试，篡改与关闭竞态拒绝并回滚。
- AC-5: 记录所选范围、实际测试计数、输出字节和耗时，以轻量 fixture 与 Harness/产品所选真实测试验收成本。

# Risks

影响分析是可审查的人类判断，不能自动证明业务语义正确；依赖清单新增消费者时必须同步。共享配置不能由所在目录推断全产品影响。认证的信任边界仍是同用户本机；产品安装输入合同未登记时禁止跨进程复用/close，使用同进程 verify --close。规范源码仍需进入 Git 历史，收尾不机械重跑同一测试。

# Verification plan

## Verification cases

- AC-1 => M08-IMPACT-SELECTION-01
- AC-2 => M08-IMPACT-SELECTION-02, M08-IMPACT-SELECTION-03
- AC-3 => M08-IMPACT-EXECUTION-01, M08-IMPACT-EXECUTION-02, M08-IMPACT-EXECUTION-03, M08-IMPACT-EXECUTION-04
- AC-4 => M08-IMPACT-CLOSURE-01, M08-IMPACT-CLOSURE-02, M08-IMPACT-CLOSURE-03
- AC-5 => M08-IMPACT-REPORTING-01, M08-IMPACT-REPORTING-02

## Gates

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5
