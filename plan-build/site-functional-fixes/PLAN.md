# 全站功能审查问题修复：计划入口

当前入口：[修复结果与剩余事项](RESULTS.md) · [阶段 6 交付清单](delivery-manifest.json) · [O001 后续修复](O001-RECOVERY.md)。
设计依据：[修复边界与验收条件](DESIGN.md)；来源：[原问题报告](../site-functional-audit/ISSUES.md)。

## 当前进度

六阶段 **23/23** 项任务全部完成并归档；I001–I004 四项原失败路径已修复，四个 Harness 规格已验证关闭。后续 O001 的无限保存恢复缺口也已修复，独立 Harness 规格已关闭；**原请求挂起的传输触发原因仍未确定**，不将恢复修复说成历史根因已定位。

| 阶段 | 修复与验证 | 任务归档 | Harness |
| --- | --- | --- | --- |
| [1 公开页面错误恢复](PHASE-1-PUBLIC-ERRORS.md) | 完成 4/4 | [phase-1-public-errors](completed/phase-1-public-errors/) | [已关闭](../../harness/specs/archive/20260912-public-error-recovery.md) |
| [2 关于页临时输入保护](PHASE-2-ABOUT-DRAFTS.md) | 完成 4/4 | [phase-2-about-drafts](completed/phase-2-about-drafts/) | [已关闭](../../harness/specs/archive/20260912-about-draft-preserve.md) |
| [3 读书封面选择与校验](PHASE-3-BOOK-COVER.md) | 完成 4/4 | [phase-3-book-cover](completed/phase-3-book-cover/) | [已关闭](../../harness/specs/archive/20260912-book-cover-media-url.md) |
| [4 Markdown 换行兼容](PHASE-4-MARKDOWN-IMPORT.md) | 完成 4/4 | [phase-4-markdown-import](completed/phase-4-markdown-import/) | [已关闭](../../harness/specs/archive/20260912-markdown-line-endings.md) |
| [5 标签 pending 观察定位](PHASE-5-TAXONOMY-OBSERVATION.md) | 调查交付完成 3/3；后续恢复修复见下文 | [phase-5-taxonomy-observation](completed/phase-5-taxonomy-observation/) | 阶段 5 无行为修改；后续单独立项 |
| [6 联合回归与修复交付](PHASE-6-REGRESSION-CLOSEOUT.md) | 完成 4/4 | [phase-6-regression-closeout](completed/phase-6-regression-closeout/) | 四项关闭与环境收尾已完成 |

当前结论与边界：

- 四个规格在各自提交快照通过 14 个精确测试引用；最终 `c31880d` 上 5 个补充联合浏览器检查通过。代码版本、检查范围与证据摘要见交付清单。
- O001 后续新增 15 秒局部等待上限、输入保留与只读核对入口；5 条正式浏览器回归及 1 条原操作序列复核通过，见 [修复报告](O001-RECOVERY.md)。历史传输触发仍需关联 trace；正常 409 不能单独证明故障恢复。
- 站内封面 Markdown 往返导入仍可能 422，是已知未修复限制；未逐一复验全部共享消费者，不宣称全站、生产或所有输入组合通过。
- 原始附件与隔离数据留 `.run/site-functional-fixes/20260912-01/`、`20260912-02/`、`20260912-03/`，O001 后续资料留 `20260912-o001/`。本轮服务与临时 worktree 已收尾，其他环境保持原样。
- 修复、测试、规格基线、正式关闭资产及交付归档均已做必要本地提交；没有推送或生产发布。本轮无待完成阶段任务。

逐任务过程、关键决定与验证结论见各阶段 `completed/`；历史记录保留当时事实，当前状态以本入口和 RESULTS.md 为准。
