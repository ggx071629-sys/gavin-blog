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

# 受影响模块验证与可信收尾

2026-09-05 用户明确要求按合并提案改造 Harness，授权范围、门禁与收尾迁移。本决策取代该文件原 A/B 优先方案；历史实现和运行记录仍保存在 Git 与本机账本。

普通任务先提交独立影响计划：改动文件、细粒度所属单元、所选 case、逐项受影响依赖及理由。`ownership.json` 保存源码与 case 归属、已知消费者。所选集合必须与 spec 的 `## Verification cases` 相等；缺失分析或错误 owner 阻断。非执行文档和精确生命周期资产默认只做结构检查；改变可执行合同的文档须显式登记影响。未知 scripts/config 文件不能默认升级 release。

固定目录 risk_routes 已从主配置移除。focused/stack 依照影响选择，release 保留为明确发布节点。旧 schema 的解析保留给历史 fixture，不是普通任务兜底。新产品模块尚未登记时须补归属和 case；当前首批覆盖 Harness 选择、执行、关闭、报告单元以及个人资料 API。

结构验证与真实收集分离。全局 module-coverage 验证 schema、模块 authority、expectations、路径和 gate 归属，不启动框架。Pytest 在执行同一进程内收集并运行精确 node ID，禁用隐式插件发现，任何 skip/失败或收集执行不一致均失败。Vitest 与 Playwright 只列出所选文件/名称/config/project，然后执行相同选择器。测试名或 collector 清单不证明业务断言语义；审查者仍需逐项核对 required/forbidden expectations。

默认关闭复用。Harness Pytest 输入身份读取所需 pytest、pluggy、packaging、iniconfig、pygments、colorama 分发文件及工具链，不遍历整套 node_modules/.venv。产品所选依赖闭包尚未登记时只允许同进程 `verify --close`，不把锁文件或 installed metadata 当作任意安装内容的真实性证明。可选持久化凭据沿用本机 HMAC 账本；同用户权限的操作者不是其防御对象。启用复用前需要确认测试实际依赖已被输入合同覆盖并测量收益。

所选 gate 在固定 HEAD 的 worktree 执行，安装目录只读用途链接，产物不跨 worktree 复用。默认不需要 Node 的 Harness 任务不会检查或链接 Web 依赖。需要生产预览的所选 Playwright quality 场景自行建立相关 Web build；不得用额外父 gate 来获取无关构建或测试证明。

verify/close 共用仓库 OS 锁与事务 journal。每次 attempt 独立保留，最新失败、中断与清理失败阻断复用。全复用运行补充来自已认证清理的隔离 check；它不声称创建了新的 worktree。close 不重跑测试/构建/collector，核对 exact evidence digest、源码/计划、AC 和归档关系。最终 runner 可以同进程关闭，避免反复 HEAD 提交与验证循环。

日志、trace、截图在隔离清理前导出到原有本机目录，维持单次 64 MiB、14 天、总量 512 MiB、日志 2 MiB 上限。Git 只保存紧凑 evidence。成功不透传子进程日志；manifest 保存输出字节代理值，计数区分实际运行与复用，失败给出诊断及本地路径。

影响判断与依赖清单的完整性仍需要人工审查；本机制证明已声明范围被真实执行，不自动证明业务影响分析无遗漏。
