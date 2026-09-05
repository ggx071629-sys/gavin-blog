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

普通任务先提交独立影响计划：改动文件、细粒度所属单元、所选 case、逐项受影响依赖及理由。`ownership.json` 保存源码与 case 归属、已知消费者及导入或跨端消费依据。所选集合必须与 spec 的 `## Verification cases` 相等；缺失分析、歧义或错误 owner 阻断。只有精确生命周期资产可以自动归为结构检查；普通文档也需显式判断，工作流等可执行合同文档还需审查消费者。未知 scripts/config 文件不能默认升级 release。

固定目录 risk_routes 已从主配置移除。focused/stack 依照影响选择，release 保留为明确发布节点。旧 schema 的解析保留给历史 fixture，不是普通任务兜底。当前源码快照按细分 Harness 工具、API 功能、Web 组件/工具和共享配置登记；结构检查使用 Git 文件清单查找未登记源码、失效路径、歧义及悬空 case，不收集产品测试。新增文件必须补归属，依赖新增/删除必须同步显式消费者。清单证明登记覆盖，不自动证明全部潜在业务依赖完备。

每个文件的 `dependencies` 是平铺的消费者判断。仅从所属单元沿 `affected: true` 的边继续审查；不受影响的边到此停止。遗漏传递消费者、重复或不可达的判断均阻断；循环只审查同一单元一次，不无限扩展。每个新增 case 保留文件、单元与具体理由。

结构验证与真实收集分离。全局 module-coverage 验证 schema、模块 authority、expectations、路径和 gate 归属，不启动框架。Pytest 在执行同一进程内收集并运行精确 node ID，禁用隐式插件发现，任何 skip/失败或收集执行不一致均失败。Vitest 与 Playwright 只列出所选文件/名称/config/project，然后执行相同选择器。测试名或 collector 清单不证明业务断言语义；审查者仍需逐项核对 required/forbidden expectations。

默认关闭复用，普通有测试任务使用 `verify --close`，不探测任何已安装分发内容。只有明确启用复用且所选 Harness Pytest 依赖合同完整时，才读取 pytest、pluggy、packaging、iniconfig、pygments、colorama 的有界分发文件及工具链，不遍历整套 node_modules/.venv。未登记安装依赖闭包时禁止跨进程关闭，不把锁文件或 installed metadata 当作任意安装内容的真实性证明。可选持久化凭据沿用本机 HMAC 账本；同用户权限的操作者不是其防御对象。启用复用前需要确认测试实际依赖已被输入合同覆盖并测量收益。

所选 gate 在固定 HEAD 的 worktree 执行，安装目录只读用途链接，产物不跨 worktree 复用。默认不需要 Node 的 Harness 任务不会检查或链接 Web 依赖。需要生产预览的所选 Playwright quality 场景自行建立相关 Web build；不得用额外父 gate 来获取无关构建或测试证明。所选浏览器测试的 `GAVIN_E2E_RUN_ROOT` 在隔离目录内创建并清理，助手的专用 config 继续拥有其独立 build/env 合同。Vitest 的可选 `--json` 输出参数放在所有 selector 之后，收集不得把源码路径当输出覆盖。

输入准备顺序为：先保存 spec，`spec-lint` 只校验规范而不要求尚未实现的 case/影响计划；集中完成代码、case、ownership、文档和独立计划，生成索引，再提交最终输入。长期文档需要引用本次 evidence 时，在提交前建立明确标为 pending 的占位 manifest；它只解决链接存在性，不构成执行证明。最终 runner 覆盖占位文件并同进程关闭。后续仅提交该次 evidence、archive、event 和生成索引，不机械重跑测试。

真实模块成本验收通过独立 `python -m tools.impact_acceptance --baseline <commit>` 完成，不挂到普通任务门禁。驱动在本地临时仓库中固定产品树、检查、安装依赖及工作负载，仅替换 Harness 引擎；逐条记录 plan、status、verify/close 的墙钟时间和输出字节，原始输出留在 `.run/impact-acceptance/`。单次测量只说明该环境该工作负载，不代表统计性性能结论或模型 token。只有真实 runner 完成关闭且总成本改善，才可据此报告优化成功。

verify/close 共用仓库 OS 锁与事务 journal。每次 attempt 独立保留，最新失败、中断与清理失败阻断复用。全复用运行补充来自已认证清理的隔离 check；它不声称创建了新的 worktree。close 不重跑测试/构建/collector，核对 exact evidence digest、源码/计划、AC 和归档关系。最终 runner 可以同进程关闭，避免反复 HEAD 提交与验证循环。

日志、trace、截图在隔离清理前导出到原有本机目录，维持单次 64 MiB、14 天、总量 512 MiB、日志 2 MiB 上限。Git 只保存紧凑 evidence。成功不透传子进程日志；manifest 保存输出字节代理值，计数区分实际运行与复用，失败给出诊断及本地路径。

影响判断与依赖清单的完整性仍需要人工审查；本机制证明已声明范围被真实执行，不自动证明业务影响分析无遗漏。
