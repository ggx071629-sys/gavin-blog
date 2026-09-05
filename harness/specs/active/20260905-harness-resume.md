---
id: spec-20260905-harness-resume
level: L1
summary: Harness 前检、认证 gate 续跑与无重复测试的事务关闭
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

实施已获 Gavin 确认的 workflow-friction_confirmed 提案 A、B。当前全局失败未统一阻断产品 gate，重试和 close 重跑全部声明 gate。本任务属于 Harness 控制面行为与信任边界变化；保持 harness-tests、harness-integrity 风险下限。

# Goal

在同 task、同 HEAD、同规范计划及受控环境内续跑；close 只消费认证证据并事务归档。

# Non-goals

不实施 C 阶段跨提交复用、Web quality 拆分、远端缓存或跨机器导入，不改产品业务代码、AGENTS.md、历史归档和发布门槛。

# Acceptance criteria

- AC-1: 全局前检、依赖或端口失败时产品 gate 调用数为零；保留停止原因与有界失败产物。
- AC-2: A、B 成功而 C 失败时下次只执行 C、D；显式 fresh 与 release 实际执行完整必需计划；新失败阻断旧成功。
- AC-3: HEAD、计划、脚本、工具链、依赖及环境漂移拒绝复用；manifest 或本机凭据篡改、丢失均无法关闭。
- AC-4: verify 成功后 close 不调用产品 gate 或 collector；并发、清理失败、中断与关闭竞态不产生假通过或半套关闭资产。

# Risks

同权限恶意进程可以读取本机密钥；本协议只防普通证据编辑和误用。保守依赖指纹有扫描成本，不宣称同 HEAD 就足够。临时存储清除后必须重验；未知输入不复用。

协议：本机记录放在系统临时目录的 gavin-harness-runs/<仓库绝对路径 SHA256>/，位于工作树之外；密钥为首次写入时生成的 256-bit 随机值。规范 JSON 使用 HMAC-SHA256 认证；每 task 的 ledger 原子替换并 fsync，记录 run、gate attempt、重试来源、输入身份、清理状态、聚合 evidence exact SHA256。仓库 manifest 仅携带紧凑引用，不能自填来源证明。所有 verify/close 使用仓库级 OS 文件锁，进程结束释放；锁忙立即失败。只选同输入最后一个 attempt，失败、未完成或清理失败不可回退；开始新运行即撤销旧聚合凭据，逐 gate 持久化，成功清理后才允许复用。中断留下 pending run，下一次 verify 标记 interrupted 并保守作废其 attempts。close 写事务 journal，异常回滚；崩溃后下次写操作先恢复，HEAD 或 evidence 并发变化拒绝关闭。只读 plan/status 不创建凭据或恢复事务。

环境：绑定当前 HEAD 完整 tree、规范 gate 配置和顺序、实际脚本/测试配置/初始化脚本（通过 HEAD）、runner/collector、平台、解释器和 Node 身份、安装依赖内容及受控传入环境；不记录密钥值，未知环境不能静默复用。不复用构建产物或服务；缺失 gate 在新的隔离 worktree 执行，已有 bundle 合同与真实阶段证明允许跳过覆盖的子 gate，统计不得重复。

产物：每 attempt 导出有限日志及测试 trace/截图到本机目录，清理前完成。单次目录上限 64 MiB、保留 14 天且总量上限 512 MiB，日志上限 2 MiB；清理只处理 runner 自有目录，不追踪符号链接。ledger 保留失败历史，不随产物清理删除；容量超限时明确报错而非删除阻断记录。端口冲突只报告端口和可取得的归属，禁止结束外部进程。

# Verification plan

## Verification cases

- AC-1 => M08-RESUME-01
- AC-2 => M08-RESUME-02
- AC-3 => M08-RESUME-03
- AC-4 => M08-RESUME-04

## Gates

- harness-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-1, AC-2, AC-3, AC-4
