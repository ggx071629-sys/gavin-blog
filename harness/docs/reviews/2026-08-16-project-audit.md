---
id: review-2026-08-16-project-audit
level: L2
summary: 2026-08-16 全项目审计历史快照
load_when:
  - historical-audit
  - audit:2026-08-16
author: Grok
---

# 2026-08-16 全项目缺陷审计

> 历史记录：结论只适用于文中固定快照，不代表当前功能、缺陷或发布状态。

## 快照

- 分支：`agent/20260815-article-detail-hifi`
- HEAD：`9921d9c44b1c64873cebd1ab278989021f93e476`
- Active spec：0；frozen spec：2（未打开、未验收、未记缺陷）
- 相对本地 `main`：超前 70；相对 `origin/main`：超前 176
- 工作树：干净，仅主 worktree
- 本机运行时：API `127.0.0.1:8000`、Nuxt `localhost:3000`；未启动 Retrieval Service（`:8101`）与清洗 Worker

## 排除与方法

排除：两条 GitHub frozen spec 及其实现/测试/决策正文；本地库内容质量（含 Test / hahaha、空项目/书摘、名片 GitHub 外链）；真实 LLM；全量 E2E 与 `quality:release`；生产部署 No-Go。

相对 08-15：上一轮以门禁 + 静态为主，漏掉了「按文档启动后孵化不可用」和「未发布栏目进入公开面」。本轮按页面走通公开与后台，并并行开 5 个只读子代理（孵化/检索、后台写作、公开搜索、文档契约、安全空转），父代理对 P1/P2 源码与已登录会话做交叉核验。

08-09、08-15 审计是历史快照。AUD26-003/004/005 的已修部分本轮复验通过，不复开；003 的残留另立新卡。

## 结论

本轮确认 **18 项缺陷：P0 0、P1 2、P2 13、P3 3**。

两条 P1 都是已声明契约被实现打穿，不是口味问题：

1. 检索服务不可用时，孵化概览与健康检查抛未捕获异常变成 500，`IncubatorShell` 把整台工作台打成错误页；待处理池自己的列表接口仍是 200。
2. 文章栏目（以及公开筛选/计数）读工作副本，不读发布修订。标题/正文/标签详情仍走修订。

08-15 修完的公开相关文案、`.env.example` 生成 Token 注释、隔离 worktree 残留，本轮未复开。

## KPI

| 指标 | 值 |
| --- | --- |
| AUD-01～20 复开 | 0 / 抽样映射项（003 残留另立，不记复开） |
| P1 且 e≥2 | 2 / 2 |
| P2 且 e≥2 | 6 / 13 |
| 文档矩阵 contradicted | 2（检索健康稳定态；检索失败不得整页打死详情） |
| 运行残留 worktree | 0 |
| 对抗复核 | 5 个只读子代理分类型审查；P1 由父代理对照源码与已登录会话复核 |

## 缺陷

| ID | 优先级 | 类别 | 结论 | 证据 | 范围 | 成本 |
| --- | --- | --- | --- | --- | --- | --- |
| AUD26-016 | P1 | F/K | 检索服务不可用时孵化概览/健康检查 500，整台工作台不可用 | 已登录动态 + 源码 | 孵化 | M |
| AUD26-017 | P1 | M/K | 未发布的栏目改动进入公开卡片、筛选和计数 | 源码高置信 | 公开阅读 | M |
| AUD26-018 | P2 | K | 检索预览把服务不可用映射成「模型未就绪」 | 源码 | 孵化检索 | S |
| AUD26-019 | P2 | F | Worker 把 `RetrievalError` 记成 `INTERNAL_ERROR` | 源码 | Worker | S |
| AUD26-020 | P2 | T/D | 测试与首启文档走 in-process/只起 uvicorn，示例环境却强制 HTTP | 源码 + 文档 | 测试/文档 | S |
| AUD26-021 | P2 | F/A | 搜索页「搜索范围」芯片不可点 | 已登录动态 | 公开搜索 | S |
| AUD26-022 | P2 | F | 已发布 slug 仍可改，409 显示成版本冲突 | 已登录动态 | 后台编辑 | S |
| AUD26-023 | P2 | F | 文章编辑器次级加载、空参考、发布失败仍会假绿或无提示 | 源码 | 后台编辑 | M |
| AUD26-024 | P2 | F | 已发布文章永久删除 409，界面无反馈 | 源码 | 回收站 | S |
| AUD26-025 | P2 | F | 文章发布不携带、不校验预期版本 | 源码 | 发布 | S |
| AUD26-026 | P2 | M | Markdown 导出写出工作副本并标 `published` | 源码 | 内容工具 | S |
| AUD26-027 | P2 | F | 孵化草稿详情加载失败不渲染 | 源码 | 孵化草稿 | S |
| AUD26-028 | P2 | F | 资料检索健康/草稿预览失败显示成未就绪或暂无 | 源码 | 孵化详情 | S |
| AUD26-029 | P2 | F | 重构预览忽略「采用建议标题/摘要」 | 源码 | 孵化草稿 | S |
| AUD26-030 | P2 | F | 发布计划先提交 `confirmed` 再执行，崩溃后不能恢复 | 源码 | 孵化发布 | M |
| AUD26-033 | P3 | F | 已发布文章预览横幅仍写「未公开草稿」 | 源码 | 后台预览 | S |
| AUD26-035 | P3 | K | 项目 JSON-LD `url` 是相对路径 | 源码 | 公开项目 | S |
| AUD26-036 | P3 | F | 「全部文章」数字是栏目计数之和，不含未分类 | 源码 | 公开文章 | S |

### AUD26-016 检索不可用变成整台孵化 500

`GET /api/v1/admin/incubator/overview` 与 `GET /api/v1/admin/incubator/retrieval/health` 都走到 `_retrieval_health` → `retrieval_client.health()`。`.env.example` 写了 `GAVIN_RETRIEVAL_SERVICE_URL=http://127.0.0.1:8101`，因此 `inprocess_allowed` 为假，客户端走 HTTP。连接失败抛 `RetrievalError("RETRIEVAL_UNAVAILABLE")`。主 API 只处理 `ApiException`；内部检索应用才有 `RetrievalError` 处理器。

本轮已登录会话：上述两个接口返回 500 纯文本 `Internal Server Error`。同会话 `GET /api/v1/admin/incubator/sources` 仍 200，且库里有资料。`/admin/incubator` 与 `/admin/incubator/inbox` 都变成「系统暂时不可用」，栈顶是 `IncubatorShell` 的 `useApiFailure(overviewError)`。所有孵化页都包了这个壳。

Worker 离线被建模成 `health[].state=blocked`。检索进程没起来却不是能力态，而是未捕获异常。`apps/api/README.md` 写明 health 返回未配置／缺失／校验失败／不可执行／stale／ready。`apps/web/README.md` 写明「检索或 LLM 健康检查失败不单独把详情页打成整页错误」。两条都被打穿。

这不是「你忘了起第三进程」的操作失误。第三进程是已声明架构；缺陷是概览把该进程当成硬依赖，而不是和 Worker 一样的能力健康。

### AUD26-017 未发布栏目进入公开读模型

`public_response` 的标题/正文/slug 来自 `ArticleRevision`。`_revision_category` 却优先 `article.category` / `article.category_id`，只有工作副本没有栏目时才回退修订快照。公开列表 `?category=` / `?tag=` 以及 `GET /taxonomy` 计数都 join 工作副本外键，不是 `article_revisions` / `article_revision_tags`。详情页标签走修订；相关文章计分也走修订。因此一次未发布的栏目 PATCH 会：

- 改公开卡片和 JSON-LD 的栏目；
- 改 `/articles?category=` 成员和栏目轨计数；
- 让详情标签（仍是旧修订）点进筛选后变成空列表。

`apps/api/README.md` 写明公开 API、搜索、站点地图只读当前发布修订。栏目是公开读模型的一部分。本轮未对线上文章做栏目 PATCH（避免改用户库）；读路径源码无歧义。`has_unpublished_changes` 会变 true，编辑器芯片方向是反的：它说「有未发布修改」，公开面其实已经换了栏目。

### AUD26-018 预览把服务不可用说成模型未就绪

`retrieval_preview` 只把 `ARTICLE_INDEX_STALE` 原样抛出，其余 `RetrievalError`（含 `RETRIEVAL_UNAVAILABLE`）一律 `503 LOCAL_MODEL_NOT_READY`。`fts_only` 在 HTTP 客户端连不上时同样进这个 except，不会降级。收件箱文案会写成「本地检索模型未就绪」。

### AUD26-019 Worker 把检索失败记成内部错误

`RetrievalError` 不是 `IncubatorError`。审计计划取回段落时只 `except IncubatorError`；未捕获的 `RetrievalError` 落到 `process_job` 的裸 `Exception`，写成 `INTERNAL_ERROR` / 「内部处理错误」。操作者看不到检索服务没起来。

### AUD26-020 测试与首启文档看不见这条路径

API 夹具 `environment="test"` 且不设 `retrieval_service_url`，`inprocess_allowed=True`。`test_incubator_workbench` / `test_retrieval_api` 的 overview/health 断言 200，从不模拟 `:8101` 拒绝连接。`failure-state-contract` 只断言壳层调用了 `useApiFailure`，所以 08-15 的 003 修完后，测试对「API 把检索宕机变成 500」仍然全绿。

根 README 与 API README 第一阶段启动只有 venv + Alembic + `uvicorn` + `npm run dev:web`。Worker 与 `run_retrieval_service.py` 出现在后面的架构段，不是启动清单。按文档复制 `.env.example` 并只起两进程，就会稳定复现 016。

### AUD26-021 搜索范围芯片是假控件

`search.vue` 在 `aria-label="搜索范围"` 下放了三个 `span.filter-chip`：01 文章 / 02 项目 / 03 阅读。`tabIndex=-1`，无 href、无 click、无 query。公开搜索 API 只有 `q`/`limit`/`offset`。文章列表把同一 class 用在真正的栏目/标签 `NuxtLink` 上。本轮 `/search?q=test` 动态确认。

### AUD26-022 已发布 slug 可改，409 被当成别人抢写

API 对已发布文章/项目/书摘改 slug 返回 409，本轮对文章 #2 PATCH `slug=deepseek-codex-audit-probe` 得到 `{"detail":"published article slug cannot be changed"}`，slug 与 version 未变。三个编辑器的 slug 输入都未禁用。`AutosaveQueue` 把任意 409 标成 `conflict`。文章编辑器文案是「服务器上已有更新。为避免覆盖内容，请刷新页面后重新合并。」操作者会以为有并发写入。

### AUD26-023 文章编辑器次级失败与发布假绿

`ArticleEditor.vue` 对栏目/标签/参考目标五个 `useAsyncData` 没有 `useApiFailure`。`failure-state-contract` 覆盖 `edit.vue` 主记录，不覆盖这个组件。标签为空时文案是「请先在栏目与标签中创建标签」，API 失败时也是这句。

「添加参考资料」会插入空 `display_title` 并在 900ms 内 PATCH，服务端 422，保存状态变成「保存失败」。`publish()` 只给缺 Alt 写 `publishError`；`apiFetch('/publish')` 没有 `catch`，flush 失败时直接 return，发布按钮闪过「发布中」后无说明。

### AUD26-024 已发布文章删不掉且无提示

`article_revisions.article_id` 是 `ON DELETE RESTRICT`。回收站 `DELETE` 把 `IntegrityError` 变成 409 `content is still referenced`。`content.vue` 的 `purge`/`restore` 没有 `try/catch`。项目/书摘修订是 CASCADE，所以只有文章这条路径会静默留下。产品承诺了永久删除；实现既不能删，也不告诉操作者为什么。

### AUD26-025 文章发布不校验版本

`POST /admin/articles/{id}/publish` 不读 body，不比较 `article.version`。项目/书摘发布带 `PublishRequest.version` 并 409。Web README 写「发布携带 flush 后的工作版本」。两个标签页时，闲置页可以发布另一页已经自动保存的工作副本。

### AUD26-026 导出把工作副本标成已发布

ZIP 写 `item.content` / `item.slug` / `item.status`，含回收站行，不读 `current_revision`。已发布且有未发布修改的文章会导出新正文 + `status: published`。公开 API 仍是旧修订。

### AUD26-027 草稿详情把加载失败做成空壳

`drafts/[id].vue` 把失败写入 `error`，模板只渲染 `actionError` / `actionMessage`，没有 `v-if="error"`，也没有 `useApiFailure`。缺资料或 5xx 时标题仍是「草稿 #id」。当前会被 016 挡住；016 修完后这条会直接露出来。

### AUD26-028 健康/预览失败显示成未就绪或暂无

收件箱详情的 `retrieval/health` 没有 `useApiFailure`；`null` 使 `indexReady` 为假，文案是模型或索引未就绪。草稿 `loadPreview` 吞掉异常后走「暂无预览。」

### AUD26-029 重构预览两边都用建议标题

`drafts/workflow.py` 的 `title_diff` 在 `use_suggested_title` 为真和为假时都取 `suggested_title`；`summary_diff` 从不看 `use_suggested_summary`。发布路径在旗标为假时保留修订标题。预览会显示不会被发布的建议文本。

### AUD26-030 发布计划确认不可恢复

`confirm` 先把计划打成 `confirmed` 并 `commit`，再逐项执行。再次进入时若状态已是 `confirmed`/`partially_published`/`published`，直接返回执行结果，不恢复。进程在 commit 之后、执行之前退出，项会停在未发布，前端把 `confirmed` 当作 in-flight 一直轮询。本条未做崩溃注入，是源码路径。

### AUD26-033 / 035 / 036

- 预览页横幅对已发布文章仍写「未公开 · 草稿预览，不会出现在公开站点」。
- 项目详情 JSON-LD `url` 用 `public_path`（`/projects/{slug}`），文章 JSON-LD 用绝对地址。
- `/articles` 「全部文章」把各栏目 `article_count` 相加；未分类是合法公开态，不会被算进去。

## 不是缺陷

| 项 | 归类 |
| --- | --- |
| 两条 GitHub frozen spec 未完成 | 已声明冻结，排除 |
| 生产未部署、本地不设 HSTS、CSP 仅为 Report-Only | `release-readiness` / Web 边界已写明 |
| 默认 `vector_backend=numpy`、Zvec 可回滚派生 | architecture decision |
| 孵化概览可见时每 10 秒刷新、Worker 空闲 1s 轮询 | 已写明的观察/串行 Worker 决策；轮询有 hidden / in-flight / backoff |
| Settings 默认 `environment=production` | 生产失败关闭默认；本轮复核仍成立 |
| 检索必须由第三进程持有模型 | 决策成立；缺陷是健康检查把它变成未捕获 500 |
| 首页「查看项目案例」在 0 个项目时仍指向 `/projects` | 站内导航，目标页有自己的空态，没有声称「已有 N 个案例」 |
| FTS5「覆盖栏目、标签」= 文章文档上的 taxonomy 字段 | 搜索页文案是文章/项目/读书；测例按栏目名命中文章 |
| `HTTPException {detail}` 与 `ApiException {error}` 双信封 | 页面失败看 status；有害实例已记在 016/022 |
| AUD26-004 相关区「adaptive / Article signal」 | `/notes/2026/08/test` 现为「章节概览 / 相关文章」 |
| AUD26-005 `.env.example` 生成模型注释 | 已含 `GAVIN_LLM_GENERATION_MAX_OUTPUT_TOKENS` |
| 本机隔离 worktree / e2e 临时库 | 上一轮已清；本轮 `git worktree list` 只有主树 |
| `9921d9c` 已含 gate process supervision | 生命周期，不是产品故障 |
| 本地文章/名片测试数据 | 内容，不是代码 |
| 公开标题/正文/搜索正文/站点地图路径在 PATCH 后仍走修订 | 通过项；017 是栏目赋值的例外 |
| 生产 fail-closed、CSRF、登录限流、媒体像素/炸弹检查 | 本轮未推翻 |

## 建议批次（未授权修改）

1. 检索不可用降为能力健康，overview/health 保持 200；壳层失败不得打死待处理池。覆盖 016/018/019/020/028。
2. 公开栏目/筛选/计数只读发布修订。覆盖 017。
3. 编辑器：禁用已发布 slug、拆开 409 语义、补 ArticleEditor 失败态、发布带 version、导出读修订。覆盖 022/023/025/026。
4. 回收站、草稿空失败、重构预览、发布计划确认窗口、预览横幅。覆盖 024/027/029/030/033 及 P3。

不要把 18 项并成一份长期 spec。P1 各需短 spec。

## 证据限制

- 未跑全量 Playwright E2E 与 `quality:release`。
- 017 未对开发库做栏目 PATCH；公开/管理当前栏目碰巧一致。
- 019/024/026/029/030 未做隔离崩溃或删除注入，依据是源码路径。
- 未读 `.env` 机密内容；检索 URL 以 `.env.example` 与运行时 500 为准。
