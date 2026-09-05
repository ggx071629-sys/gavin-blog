---
id: decision-verification-resume
level: L1
summary: 同提交认证续跑、失败阻断和只消费凭据的事务关闭
load_when:
  - verification
  - task-close
  - harness-change
author: Gavin
---

# Verification resume and attestation

实施已确认提案的 A、B 阶段。`plan <task>` 解释执行与复用理由，不调用产品测试或 collector；`verify <task>` 执行全局前检、当前合同解析和缺失 gate；`status <task>` 只读报告状态；`close <task>` 消费已认证的完整聚合证据。`verify <task> --fresh` 禁用结果复用；release profile 和包含 release 的计划始终 fresh。现有发布入口和门槛保持不变。

本决策替代 [旧 attestation 决策](20260901-verification-attestation.md) 中“close 必须重新运行 task verify”及其必要成本论断。继续保留规范命令、真实 collector、AC 覆盖、清理结果及 archive/event/exact evidence digest 的一致性检查，不重写历史资产。

## Inputs and execution

初版只支持同 task、同 HEAD 完整 tree、同 gate 顺序及合同的续跑。身份包括 spec、文档目标 blob、风险下限、规范脚本、测试/初始化配置、runner/collector、执行平台、解释器可执行文件与实际运行时版本、Node 可执行文件、本地安装依赖内容与受控环境摘要。依赖扫描排除生成的 Python bytecode、`__pycache__`、`.cache`、`.vite`；这些目录不能承载 gate 的可执行输入。已在 package.json 声明且由同一 HEAD 约束的 workspace 链接（含 Windows junction）只绑定目标，不扫描目标内生成产物；安装包内容仍逐文件计算摘要。未知可执行依赖、缺失目录和其他越界链接拒绝验证，不推测可以复用。

gate 与 collector 仅继承 `verification_inputs.ENVIRONMENT_KEYS` 中的 OS/工具定位字段并设置 CI 与 Python 确定性开关；任意外部应用密钥、测试标记、端口或构建开关不透传。应用环境由已提交的规范测试入口建立。manifest 不保存密钥值。修改受控字段或依赖内容使凭据失效。验证前后分别检查输入，处理中漂移的运行不可复用。

每轮缺失 gate 在新 detached worktree 中执行，不复用旧服务或构建产物。完整父 gate 的规范合同与实际完成 proof 可覆盖显式子 gate；执行/复用/覆盖均有来源，不重复汇总测试数。全局前检失败阻断全部产品 gate；依赖与 E2E 默认端口在昂贵 gate 前检查。端口冲突只报告归属，不结束外部进程。

## Local trust protocol

本机目录为系统临时目录下 `gavin-harness-runs/<仓库绝对路径 SHA256>/`，不在 Git 工作树内。首次写入生成 32 字节随机密钥，使用 HMAC-SHA256 认证规范 UTF-8 JSON ledger。每 task 独立 ledger 保存 run、输入、gate attempt、retry_of、清理状态和聚合 evidence exact SHA256。仓库 evidence 的 `execution.receipt` 与 check `provenance` 仅引用这些记录。

ledger 使用临时文件、fsync、原子 replace 发布；开始新运行立即撤销旧聚合凭据。每个 gate 启动前落盘 pending attempt，完成后落盘结果；只有已结束且清理成功的运行中最后一次成功 attempt 可复用。同输入新失败或 pending 阻断旧成功；再次通过保留 retry_of 和失败历史。close 同时校验 HMAC、exact evidence bytes、当前输入、最后 attempt、覆盖和清理，不接受普通 JSON 自报成功。

仓库级 OS 文件锁覆盖 verify/close，进程退出自动释放；并发操作立即报告锁忙。崩溃留下 running 的 run 在下次 verify 转为 interrupted，相关 attempts 不可复用。close 开始前写认证事务 journal，异常恢复 active spec 并删除本次 archive/event；下次写操作先恢复遗留事务，外部编辑冲突时停止并保留 journal。HEAD、源 spec 或 evidence 并发变化均阻断关闭。plan/status 只读，不执行恢复。

该边界防误改、普通 evidence 编辑和陈旧复用，不防能读取同一用户目录的恶意进程。临时目录被系统清理、凭据丢失、认证失败时重新执行；`--fresh` 会保留损坏 ledger 的诊断副本并建立新记录，不能恢复旧通过。无跨机器导入。远端 CI 身份绑定另行设计。

## Diagnostics and checks

断言、启动、端口、超时、收集与清理失败分别记录，未开始的后续 gate 保持 not-run。每 gate 本地日志上限 2 MiB，每运行导出 trace/截图等产物上限 64 MiB，超限记录省略数量；产物保留 14 天，总量上限 512 MiB，后续运行只清理 runner 自有目录。ledger 不随产物清理删除，超过 16 MiB 时明确停止。日志和产物不提交到 Git。

verify 执行全部全局 checks。close 运行关闭资产检查，唯一省略的是 `module-coverage` 的完整 collector；其 proof 已由同输入认证聚合证据覆盖。新增全局 check 默认仍在 close 执行，不默认为可省略。归档、event、exact digest 和恢复检查继续执行。

跨提交按路径失效、Web quality 拆分及构建产物复用属于 C 阶段，需先依据真实耗时评估，不能由本决策自动启用。
