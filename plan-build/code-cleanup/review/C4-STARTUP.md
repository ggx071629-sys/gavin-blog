# 启动验证输入与环境限制

2026-09-11。产品提交 c73071e；这些结果是启动补充检查，不替代 Harness 正式测试证据。

## 已执行

在固定提交的独立 worktree 中链接既有依赖，使用临时 SQLite/媒体及测试专用配置，不读取本机 .env、不访问真实库。普通 API 采用现有 uvicorn 工厂命令，Web 用 npm run dev:web；离线助手用 npm run dev:assistant。

| 模式 | API 健康 | Web 首页 | Web→代理→文章 API | 其他 |
| --- | --- | --- | --- | --- |
| 普通开发 | 200 | 200 | 200 | Web 使用其实际绑定 localhost:3000 |
| 离线问答 | 200 | 200 | 200 | availability 200；没有提交问题或调用真实模型 |

成功启动检查耗时 45.55 秒，worktree、依赖链接与本任务服务进程已清理；只停止本任务启动的进程。日志留本机 `.run/cleanup/startup-1789125622078424600/`。

首次探测误用 127.0.0.1 而普通 Nuxt 默认绑定 localhost，首页探测超时；修正探测地址后相同产品提交通过，未改应用配置或放宽状态码检查。初次日志保留于 `.run/cleanup/startup-1789125468467819800/`。

## 前次真实环境阻塞（已解除）

启动任何临时服务前，默认真实 Web 3101、API 8101、E5 8091、Qdrant 8092 的只读探测均未能建立 HTTP 响应。已询问用户是否有其他运行地址；目前没有获得新的地址。

因此没有取得真实问答服务、worker 与有效资料读取的当前成功结果。没有为清理验收启动真实模式、迁移真实库、重建索引、读取密钥或提交付费问题。普通/离线服务通过不能替代这部分结果。

以上为前次执行时的限制，后续用户已明确授权读取现有本机配置并直接启动真实项目；本次结果如下。

## 真实环境验收与既有遗留

2026-09-11，源码提交 `501cda272b615d413e6e68264a36b0ba0de604fe`。采用既有 `scripts/local_launcher.py start --no-browser`，由它运行 `npm run dev:assistant:real` 及独立 worker/E5/Qdrant。配置在进程内读取，不输出或提交密钥。内容库为 `apps/api/data/e5/content-verified.db`，runtime 为 `data/assistant-local-real/assistant_runtime.db`；启动前 SQLite backup 留在 `.run/cleanup/real-c4/`。两库已分别处于内容 0030、runtime rt0004，启动后版本未变。

| 检查 | 结果 |
| --- | --- |
| Web 3101 / API 8101 | 首页及 API 健康 200；6 个公开/availability 接口直连与同源代理内容一致，available=true |
| Worker | 独立进程存活，同一 owner 心跳连续推进，fence=16 |
| E5 8091 | 鉴权及固定模型身份通过，真实 query 嵌入 384 维 |
| Qdrant 8092 | 鉴权通过，active 集合 e5_verified_14 为 green，25 个向量对应 25 个规范切片 |
| 有效来源 | 3 篇文章、1 份个人资料、1 份简历均有当前版本切片；4 次非 Chat 检索各读取 5 个有效候选，版本逐条校验，codex 同时有 FTS/dense 命中 |
| 简历 | 应用 status_view 为 ready/usable；存储层 indexing 经当前版本投影得到 ready，未改状态；同源 PDF 200，261840 字节，SHA-256 与当前库版本一致 |
| GSAP | 原有 orb-motion.spec.ts 直接指向真实站点，无 API mock，1 项通过（测试执行 10.6 秒）；覆盖暂停、滚动、可见性、两次导航清理、减少动态效果、移动端、明暗主题无障碍与浏览器错误 |
| 停止与保留 | 仅停止本任务启动的实例；3101/8101/8091/8092/8093 全部释放。内容/索引/任务/费用及其余表行摘要不变，仅 worker 心跳、daily metrics、runtime cleanup/gate 正常变化 |

紧凑补充证据：[C4-REAL.json](C4-REAL.json)。原始检查脚本、失败尝试、浏览器结果、备份和前后摘要留本机 `.run/cleanup/real-c4/`；服务日志位于 `.run/quick-start/7ba2743425514165baabe055071dc019/`。没有提交付费 Chat，没有 rebuild/finalize，没有新增测试替身或修改产品代码。

### 遗留处置

- **L-C4-01：既有 FTS 覆盖缺口。** 启动前和停止后，第 14 代均为 25 个规范切片/向量、9 条 FTS；nginx 在 active FTS 无命中，dense 仍返回当前有效资料。额外完整性断言未通过，不能以 retrieve 返回 ok 宣称 FTS 完整。与本次清理无新增数据差异；遵守用户保留数据、不重建索引的边界，保留现场，后续应单独调查多代 FTS 一致性。C4-03 只验收服务连通、有效资料读取与动效，不据此宣称完整召回或问答质量通过。
- **L-C4-02：历史任务。** 第 15 代 staging/ready_to_switch 及失败任务 5、6（article 1/v6、article 2/v7，index_task_failed）在备份和停止后均未改变；当前代已有这两个版本的切片。未自动 retry、删除、切换或重建。
- 检查器首次误用 `/about`、`chunk.body` 和原始简历 state；按现行 `/about-page`、`page_content`、`status_view` 修正本机脚本后通过。nginx FTS 失败独立保留为 L-C4-01，没有写成通过。
- 本轮没有付费 Chat、供应商当前输出质量、完整 FTS 召回或生产资格结论；现有 probe 签名与绑定验证通过不替代这些验证。

## 后续完整性修复（2026-09-11）

原FTS缺口已由[索引完整性任务](../../index-integrity/PLAN.md)修复：相同chunk_id的删除限定generation，新增启动/ready/finalize硬门槛。备份后仅补齐active第14代16条FTS，5份当前公开来源独立推导25条切片，规范切片/FTS/Qdrant逐条零差异。其他代FTS与全部11个向量集合摘要不变，重复修复零变更；真实服务、引用/PDF及GSAP复验通过并正常停服。原记录保留历史，见[新验收证据](../../index-integrity/REAL.json)。
