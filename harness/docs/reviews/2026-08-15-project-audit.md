---
id: review-2026-08-15-project-audit
level: L2
summary: 2026-08-15 全项目审计历史快照
load_when:
  - historical-audit
  - audit:2026-08-15
author: Grok
---

# 2026-08-15 全项目缺陷审计

> 历史记录：结论只适用于文中固定快照，不代表当前功能、缺陷或发布状态。

## 快照

- 分支：`agent/20260815-article-detail-hifi`
- HEAD：`f5f0daf170ae956532837fe9b7e506950ec45e98`
- Active spec：0；frozen spec：2（未打开、未验收、未记缺陷）
- 相对本地 `main`：超前 62；相对 `origin/main`：超前 168
- 工作树：仅未跟踪 `.grok/`（本审计合同）

## 排除与方法

排除：两条 GitHub frozen spec 及其实现/测试/决策正文；本地库内容质量；真实 LLM/GitHub；全量 E2E 与 `quality:release`；生产部署 No-Go。

已执行：AUD-01～20 映射的 pytest / vitest / failure-state；Harness 全局 `verify` 与 evidence inventory；文档对照；静态扫描；检索/反链/分页/名片追加测试；公开读取路径交叉核对。

08-09 审计与 `.run` 中 08-11/08-12 记录是历史快照，不是本清单。

## 结论

没有发现 P0/P1。公开发布快照、搜索、sitemap、反链、Worker 启动校验、媒体解码前像素检查、公开失败态，以及 AUD-01～20 对应自动化检查均通过。

本轮确认 **4 项缺陷：P0 0、P1 0、P2 3、P3 1**。另有一组已声明技术决策，不当作缺陷。

## KPI

| 指标 | 值 |
| --- | --- |
| AUD-01～20 复开 | 0 / 抽样映射项 |
| P2 且 e≥2 | 0 / 3（三条 P2 均为静态高置信） |
| 文档矩阵 contradicted | 1 |
| 运行残留 worktree | 1 |
| 对抗复核 | 本轮由同一执行者完成，未再开独立否决子代理 |

## 缺陷

| ID | 优先级 | 类别 | 结论 | 证据 | 范围 | 成本 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD26-003 | P2 | F | 孵化概览与后台编辑把 API 失败显示成空成功 | 静态高置信 | 后台 | M |
| AUD26-004 | P2 | F | 公开相关区把「adaptive N items」渲染给读者 | 静态高置信 | 公开阅读 | S |
| AUD26-005 | P2 | D | `.env.example` 仍写生成模型本阶段不调用 | 静态高置信 | 配置文档 | S |
| AUD26-001 | P3 | I | `gavin-publish-iso` 隔离 worktree 未清理 | 动态复现 | 本机 Harness 残留 | S |

### AUD26-003 孵化概览与后台编辑把 API 失败显示成空成功

`apps/web/pages/admin/incubator/index.vue` 在 `overview` 为空时走 attention 的 `v-else`，文案是「当前没有需要处理的异常或待办」。`IncubatorShell.vue` 对 overview 使用 `.catch(() => null)`，角标变成 0。文章/项目/书摘/名片编辑页只写 `v-if="data"`，没有 `useApiFailure`。

公开列表/详情和后台**列表**已有失败分型，且 `test:failure-states` 全绿。`failure-state-contract.test.ts` 的 admin 名单不含孵化与编辑页，所以这是假绿盲区，不是 08-09 AUD-04 回归。

修复需要扩大失败态契约，建议独立短 spec。

### AUD26-004 公开相关区把布局实现词渲染给读者

`notes/[year]/[month]/[slug].vue` 相关区标题为 `Related / {{ relatedCountLabel }}`，计算值是 `adaptive single item` / `adaptive N items`。这是 V2 布局说明，不是读者文案。同页还有无中文对照的 `Article signal`。`article-reading` e2e 覆盖 V2 外观，不断言这些字符串。

公开文章契约未变；这是阅读壳层缺陷。

### AUD26-005 `.env.example` 仍写生成模型本阶段不调用

`apps/api/.env.example` 第 32 行仍写「本阶段只显示 generation model 配置状态，不调用生成模型」。草稿生成已使用 `generation_max_output_tokens`。操作者按示例理解会判断错误。改注释并补 `GAVIN_LLM_GENERATION_MAX_OUTPUT_TOKENS` 即可，不需要 spec。

### AUD26-001 隔离发布 worktree 未清理

`git worktree list` 仍有 `C:/Users/Administrator/AppData/Local/Temp/gavin-publish-iso/worktree`，停在祖先 `9029094`。仓库内没有该路径名，不能据此断言当前 `isolated_verification.py` 必漏清理。这是本机运行残留。

## 不是缺陷

| 项 | 归类 |
| --- | --- |
| 两条 GitHub frozen spec 未完成 / 本分支无其实现 | 已声明冻结，排除 |
| 生产未部署、本地不设 HSTS、CSP 仅为 Report-Only | `release-readiness` / Web 边界已写明 |
| 默认 `vector_backend=numpy`、Zvec 可回滚派生 | architecture decision |
| 孵化概览可见时每 10 秒刷新、Worker 空闲 1s 轮询 | 已写明的观察/串行 Worker 决策 |
| Settings 默认 `environment=production` | 生产失败关闭默认 |
| `agent/20260815-gate-process-supervision` 未合入本 HEAD | 分支状态，不是产品故障 |
| `f5f0daf` 在 close 后补 V2 阅读壳 | 过程事实；其中错误文案已记为 AUD26-004 |
| 本地文章/名片测试数据 | 内容，不是代码 |
| 普通 `__pycache__` | 构建产物 |
| Harness 全局 verify 全绿、公开失败态 5/5 通过 | 通过项 |

## 证据限制

- 未跑全量 Playwright E2E 与 `quality:release`。
- P2 三条未做隔离浏览器复现；模板与注释已足够定性。
- 未读 `.env` 内容，未改开发库。
