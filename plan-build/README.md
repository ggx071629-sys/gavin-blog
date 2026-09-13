# 实施计划与验收资料

按主题集中保存设计依据、实施计划、阶段记录和测试报告。每类计划使用一个目录，原文件名保留以便检索与追溯。

| 主题目录 | 资料内容 | 阅读入口 |
| --- | --- | --- |
| `assistant-gap-closure/` | 知识问答 18 项缺口的六阶段执行计划；32 项任务未开始，生产阶段按目标与授权条件执行 | [计划入口](assistant-gap-closure/PLAN.md) |
| `site-functional-fixes/` | 六阶段 23/23 归档、4 项缺陷修复；后续 O001 无限保存恢复缺口已修复，合计 5 个规格关闭，历史触发原因未定 | [结果索引](site-functional-fixes/RESULTS.md) · [计划入口](site-functional-fixes/PLAN.md) · [O001](site-functional-fixes/O001-RECOVERY.md) |
| `site-functional-audit/` | 真实浏览器审查已完成，31 项任务归档；审查时的 4 项缺陷已由后续修复计划交付，原报告保留；邮件闭环与 AI 排除 | [计划入口](site-functional-audit/PLAN.md) |
| `code-cleanup/` | 清理已归档；原 FTS 缺口已在后续索引完整性任务修复并实测 | [计划入口](code-cleanup/PLAN.md) |
| `index-integrity/` | 多代 FTS 隔离、逐条对账、真实库定向补齐与完整性验收 | [修复计划](index-integrity/PLAN.md) |
| `account-management/` | 账号管理设计、四阶段计划、后端/UI/验收记录 | [主计划](account-management/ACCOUNT-MANAGEMENT-PLAN.md) |
| `assistant-upgrade/` | 助手关于页与简历接入、契约、四阶段计划和验收记录 | [主计划](assistant-upgrade/ASSISTANT-UPGRADE-PLAN.md) |
| `assistant-safety/` | 助手逐块支持、输入防护与 Codex 离线评审；16/16 完成，保留语义漏检/误拒与未上线边界 | [计划入口](assistant-safety/PLAN.md) · [知识问答缺口审查](assistant-safety/reviews/20260912-knowledge-qa-gap-analysis.md) |
| `chat-readiness/` | Chat 运行校验、重启、复验与账本恢复 | [主计划](chat-readiness/CHAT-READINESS-PLAN.md) |
| `studio-ui/` | 写作台六阶段计划、设计基线与完成记录 | [主计划](studio-ui/STUDIO-UI-PLAN.md) · [设计资料](studio-ui/design/README.md) |
| `local-qa/` | 本机 E5 与 Chat 建设计划、阶段归档和验收参考 | [主计划](local-qa/build-qa.md) |
| `capacity-tests/` | 2 核 / 4 GB 环境的并发复测、资源统计与报告附件 | [初测报告](capacity-tests/2c4g-blind-test-report.md) · [复测报告](capacity-tests/2c4g-retest-concurrency-rebuild.md) |
| `ui-improvement/` | 全站视觉审查、UI 改造计划、设计原型和验收资料 | [审查报告](ui-improvement/UI_AUDIT_REPORT.md) · [阶段计划](ui-improvement/design/PHASE-2.md) |
| `ui-refinement/` | 第二版工程设计稿、页面预览与实施验收记录 | [实施记录](ui-refinement/IMPLEMENTATION.md) |

原根目录 `completed/` 的记录已按主题分入各目录下的 `completed/`；原 `build-qa/` 的 `archive/`、`reference/`、`tasks/` 合并至 `local-qa/`；原 `tset-report/` 更名为 `capacity-tests/`。

`harness/` 继续在原位置管理正式规格、验证证据与研发流程，本目录通过链接引用它们。历史证据中的旧路径描述其生成时的仓库状态，不改写历史证据。原型附件、原始截图和大型报告沿用原有 Git 忽略边界；本机日志、数据库、依赖、迁移备份及独立 `web_prototype/` 不属于本次实施资料归集。

后续同主题的设计、计划与报告继续放入对应目录；新主题在此新建一个目录并补充入口。文档链接相对于文档自身位置，命令仍按文中指定的工作目录执行。
