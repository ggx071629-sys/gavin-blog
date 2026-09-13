---
id: decision-harness-execution
level: L1
summary: 干净快照预检、显式前置任务、诊断边界与精确测试身份
load_when:
  - verification
  - harness-change
author: Codex
---

# Harness 执行合同

2026-09-06 用户根据执行成本提案明确授权实施 A–C。D 需要独立规格与评审，`reuse=false` 保持不变。

正式 verify 先检查工作区，再在固定 HEAD 的 detached worktree 中执行纯结构、链接、索引、归属及完整影响计划检查。该检查在依赖链接、collector、prepare 和产品测试之前完成；快照失败时消费者为 not-run。成功快照检查承担本轮 harness-integrity gate，不重复执行。close 对新 archive/event/index 事务状态的检查仍执行。

所选 JavaScript 测试显式消费 nuxt-prepare；production quality 还消费 quality-build。每项前置任务声明命令、cwd、环境、输出、输入摘要、消费者和失败分类。收据只存在于本轮固定 worktree，输出缺失必须重建；不跨 worktree 复用。assistant 的带开关构建继续由其服务配置拥有，普通 dev/failure 配置与生产环境不混批。Harness-only 不初始化 Node。

`diagnose TASK --case CASE` 从完整计划选择精确引用，`diagnose TASK --failed` 从最新正式运行的可信阶段消费者恢复子集并匹配当前计划。引用消失、歧义、旧记录没有阶段来源时报告 diagnostic gap。诊断仍要求提交后的固定 HEAD，结果保存在本机独立 diagnostics 命名空间，不修改正式 evidence、aggregate 或授予关闭资格。诊断通过后正式 verify 仍完整执行。修复期间先做局部检查，再提交完整输入进行正式验收；运行中输入变化继续使认证失败。

选择协议版本为 3，完整身份包括 kind/config/project/仓库路径/title_path。旧模块引用允许保留叶标题，但 collector 必须唯一解析；歧义引用需同时补齐 config、project、title_path。新协议使旧输入身份失效，历史 evidence 不改写。Pytest 核验 node ID 集合；Vitest 和 Playwright 用结构化报告比对收集与执行身份集合，拒绝扩张、重复、遗漏、skip、失败及重试。Playwright test-list 的前缀语义不能替代集合核验，无法无损表示时回退单身份文件/正则选择，仍做相同集合核验。

浏览器批次默认按单身份独立 runtime。只有配置显式列入 shared_test_paths 且开启 merge_playwright 时，兼容 gate/config/project 的共享测试才合批；列表声明者必须已验证独立、合并及不同顺序的数据前提。每批只使用自己启动的服务，不共享跨运行服务。未声明、需要空数据库或修改全局数据的测试维持单身份隔离，不推断同文件安全。

产物位于 run/gate/batch 目录，后续调用不能清理前批截图。导出维持原 64 MiB 单次、512 MiB 总量和 14 天期限；阶段日志、原始报告、截图均留本机，Git 只保留紧凑证据。阶段分类来自 runner，日志启发式仅作 hint。结果身份失败、输入漂移、导出或清理失败均不能认证。

批处理开关初始关闭。当前实现不宣称已降低真实 42 项工作负载的墙钟成本。启用前须在相同产品树、测试、依赖、浏览器和数据策略上至少完成三对交替 before/after，保留失败样本，报告中位数、范围、批次数和服务启动数。不能把历史 470 秒样本与不同 fixture 的新结果直接相比；未满足门槛继续保持保守执行。跨提交认证复用属于后续 D，不由这个开关启用。
