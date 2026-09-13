# 全站功能修复：交付结果

2026-09-12：六阶段 23/23 项任务完成；I001–I004 的原失败路径均有修复证据，四个 Harness 规格已通过确定性关闭。后续按追加要求修复了 O001 的无限保存恢复缺口，独立规格也已关闭；原请求挂起的传输触发原因仍未确定。详见 [O001 后续修复报告](O001-RECOVERY.md)。

原始事实保留于 [问题报告](../site-functional-audit/ISSUES.md) 与 [覆盖清单](../site-functional-audit/COVERAGE.md)，不把当时的失败改写为通过。本轮范围、排除项与验收沿用 [设计依据](DESIGN.md)。

## 修复与正式证据

| 问题 / 原案例 | 验证代码提交 | 精确引用数 / 结果 | Harness 归档与证据 |
| --- | --- | --- | --- |
| I004 / C070 | `8d5728e` | 5 / 全通过 | [20260912-public-error-recovery](../../harness/specs/archive/20260912-public-error-recovery.md) · [证据](../../harness/verification/evidence/20260912-public-error-recovery.json) |
| I003 / C031 | `c9ae20a` | 3 / 全通过 | [20260912-about-draft-preserve](../../harness/specs/archive/20260912-about-draft-preserve.md) · [证据](../../harness/verification/evidence/20260912-about-draft-preserve.json) |
| I001 / C024 | `2064df1` | 2 / 全通过 | [20260912-book-cover-media-url](../../harness/specs/archive/20260912-book-cover-media-url.md) · [证据](../../harness/verification/evidence/20260912-book-cover-media-url.json) |
| I002 / C045 | `81bdd48` | 4 / 全通过 | [20260912-markdown-line-endings](../../harness/specs/archive/20260912-markdown-line-endings.md) · [证据](../../harness/verification/evidence/20260912-markdown-line-endings.json) |

- I004：初次客户端导航失败呈现错误页；重试与站内恢复可用，搜索关键词保留，SSR 503 和缺失详情语义保持。
- I003：自动保存回声保留未提交标签；提交后清空，领域排序删除同步维护临时输入，领域上限仍有效。
- I001：媒体库站内封面通过前后端校验；保存刷新、正文预览、发布及无登录访客加载同一图片通过；HTTP(S) 与非法地址校验保留。
- I002：文章、项目、读书 LF/CRLF 同内容导入一致且仅产生草稿；非法 front matter/YAML/编码仍拒绝，ZIP 导出与重复导入语义通过。

以上共 14 个精确测试引用（4 个 Pytest、10 个 Playwright），全部实际执行并通过；M08 文档结构检查另外由 Harness 执行。各任务在表中各自提交的 detached worktree 中验证，不能把四份证据说成同一 HEAD 的一次全量测试。后续任务未改变先前修复的运行时代码；最终联合回归在 `c31880d` 上完成。

## 阶段 6 联合回归与版本

最终提交快照上的 5 条补充 Playwright 检查全部通过：关于草稿预览与显式发布隔离、文章 390×844 筛选布局、读书真实发布列表及 390×844/1440×900/1024×800 布局、搜索空态/命中/分页保持关键词、重复标签 slug 的 5 次真实 409 与按钮复位。默认桌面 Chromium 视口为 1280×720；移动仅视口模拟，不是真机。

初始 HEAD 为 `551dcc9`，回归测试与消费者登记提交为 `c072369`。实现、规格引入和关闭按任务交错提交；精确代码版本、evidence SHA-256、归档及完成事件路径见 [紧凑交付清单](delivery-manifest.json)。本轮只做本地提交，没有推送或生产发布。

本地运行索引：`.run/site-functional-fixes/20260912-03/README.md`、`supplementary.json`、`cleanup.json`；新正式 runner 日志副本在该目录 `harness-logs/`。历史反证与关联证据继续位于 `20260912-01/`、`20260912-02/`；原始日志、数据、截图和备份不提交。

## O001 后续交付与剩余限制

- **O001 恢复缺口已修复**：栏目/标签保存与删除持续无响应时，15 秒后保留输入并提示结果未确认，提供有界 GET 核对，不自动重发写请求。修复前失败反证、修复后 5 条正式回归和 1 条原操作序列复核均有记录；实现 `74696da`，关闭 `cdc79a8`。原请求 #4950 的传输触发原因仍未知；无访问日志不能证明未到 API，解释与证据见 [后续报告](O001-RECOVERY.md)。这是阶段 6 之后的独立修复，不改写其历史交付清单。
- **已知未修复限制**：站内封面虽能保存发布，但 Markdown 导入元数据仍仅接受 HTTP(S)；包含站内封面的导出文件直接重新导入会 422。本轮保留该边界，未宣称媒体封面往返导入成功。
- **未验证范围**：未逐一复验全部 `useApiFailure` 消费者、所有共享写作台组合或全站 74 组；旧关联证据按未变化路径引用，不代表当前全量通过。邮件闭环、AI、生产部署、多浏览器、真机和质量评分仍排除。
- **阻塞**：本轮授权交付无未解决阻塞；保留 O001 历史传输触发原因未知的边界。其他任务的 active 规格保持原样，不纳入关闭数量。

## 环境与归档

四轮 Harness evidence 均记录 `cleanup_status=passed`，本轮临时 worktree 已清理。补充检查结束后 3100/8100/3200/8200 无监听；异常拦截随测试上下文撤销。补充专属数据库与媒体保留在 `.run/site-functional-fixes/20260912-03/supplementary-data/` 供复核，既有数据、服务和其他 worktree 未清理。

任务过程及输入缺口的实际修正见 [阶段 6](PHASE-6-REGRESSION-CLOSEOUT.md) 与其四份归档；返回 [总计划](PLAN.md)。
