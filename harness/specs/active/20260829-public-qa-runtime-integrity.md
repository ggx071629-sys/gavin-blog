---
id: spec-20260829-public-qa-runtime-integrity
level: L1
summary: 闭合公开问答在 runner fencing、Saver 清理、浏览器删除竞态与公开合同上的已知语义缺口
load_when:
  - task:20260829-public-qa-runtime-integrity
author: Gavin
task_id: 20260829-public-qa-runtime-integrity
status: active
verification_profile: release
verification_escalation: 本任务同时修正匿名付费 runner、LangGraph checkpoint、保留期清理、公开 API/OpenAPI、浏览器 DELETE 与无障碍竞态；任何单栈门禁都不能证明跨 owner 的迟到写入和端到端隐私语义，必须使用完整 release bundle。
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
  - harness/docs/product/brief.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/operations/release-readiness.md
  - harness/docs/decisions/20260829-public-qa-runtime-integrity.md
documentation_reason: 本任务会修正公开问答的执行所有权、LangGraph checkpoint 清理、原文保留、浏览器删除语义、多轮上下文和公开错误合同，并调整后续管理面与生产资格路线，必须同步项目、应用、契约、产品、架构、运维与持久决策文档。
state_history:
---

# Context

第三阶段 `20260829-public-qa-web-delivery` 已在当前 feature 分支形式关闭：归档、schema v2 evidence 和 completed event 均存在，evidence 对提交 `a156943` 报告 release profile 通过。该事实证明 Harness 生命周期已经完成，不证明每项验收语义都被有效测试或实现，也不证明提交已经进入 `main` 或生产环境。现有 release 文档仍明确将真实供应商、反向代理 SSE、2 vCPU／4 GB 实机、持久化与备份恢复列为生产阻断项。

关闭后的只读代码审计发现，第三阶段依赖的若干硬前置仍与实现直接冲突：

- `graph.py` 的 stage event、terminal、history 与 hub publish 没有使用已存在于 graph state 的 fencing token；`store.py` 只检查 session 当前可用，旧 owner、过期 lease 或被 DELETE fence 的 runner 仍可能写入或发布迟到内容。
- `runner.py` 在 `AsyncSqliteSaver.adelete_thread()` 真正完成前写入 `checkpoint_deleted_at`，删除失败只记录 warning；cleanup 也先标记再异步删除，48 小时路径会吞掉 Saver 表的 `OperationalError`。因此数据库中的“已删除”不一定是事实。
- 256 KiB 统计在读取 `checkpoints`／`writes` 失败时把它们当作 0 字节，15 分钟 body purge 也没有清除 attempt 的 `parsed_json`／`vector_json`，会让隐私上界和 breaker 状态失真。
- retrieval 节点把含正文的 hydrated evidence 直接放入 LangGraph state，因而会复制进 checkpoint；这违背第二阶段“checkpoint 只保存 generation／version 绑定 descriptor、模型调用前临时 hydration”的既有边界。
- `AssistantHost.vue` 在确认 DELETE 前没有停止旧 polling，`refreshStatus()` 也没有 stream generation guard，已经清空的正文可能被一个迟到 GET 再次写回 Vue 状态。
- questions 的 OpenAPI 仍包含 FastAPI 默认 422；response URL 只用 `endsWith()` 检查 path；textarea 仍有可恢复表单 `name`；移动导航与助手可能同时持有 modal；轮询没有兑现 `Retry-After` 状态语义。
- GET session hydration 会把 `view.turns` 直接交给组件渲染，恢复答案没有经过 SSE answer 已使用的 marker／citation／source／path 闭包校验，异常 path 可直接进入 `NuxtLink`。
- 检索 query 会读取最近历史问题，但生成消息把 `history_text` 固定为空；这与已披露“最近最多 4 轮问答会发送给云端模型”的多轮能力不一致。

现有测试没有覆盖这些边界：部分断言恒真或不验证结果，enabled assistant E2E 只有完成答案后的 happy path reload，没有 active-turn reload、DELETE、迟到 GET、Saver failure、terminal→DELETE→publish、全字段字节上限、双 modal 或真正多轮指代场景。因此不能把测试数量等同于唯一且有效的验收覆盖。

原路线中管理员启停、健康、索引队列和费用控制面仍是已确认需求，但它依赖可信的 runtime、cleanup 与费用事实。第四阶段先收敛为本语义闭合任务；管理员运营控制面顺延为下一独立阶段，真实环境生产资格在其后单独验收，避免把已知错误状态包装成可运营或 production-ready。

# Goal

在保持公开问答默认关闭、现有单 API owner、独立 runtime SQLite、`AsyncSqliteSaver`、LangGraph 图拓扑、RAG 索引和费用数值不变的前提下，使一次 turn 从准入、provider dispatch、checkpoint、event、terminal、publish 到删除和保留期清理都服从同一可验证的执行身份与顺序。失去 lease、session epoch 变化、DELETE、过期或 cleanup failure 后，旧 runner 只能对已经发送且结果未知的 attempt 做不含原文的保守费用结算，不能再提交正文、history、event、checkpoint 或 live delivery。

同时闭合浏览器 controller 的 DELETE generation fence、精确同源响应校验、轮询状态机、overlay ownership、稳定 400 合同和真实多轮上下文。所有修复必须由离线、确定性的 API barrier、Web 受控时钟和 Playwright 场景证明；此前的 archive 与 evidence 保持历史原样，新 evidence 只能证明本任务提交。

# Non-goals

- 不建设 `/admin/assistant`、在线启停、健康／费用看板、Worker heartbeat、人工重试或全量重建控制面；这些属于下一独立阶段。
- 不启用真实访客流量，不选择或探测真实模型供应商，不决定部署平台、域名、TLS、反向代理、进程管理、备份恢复或 2 vCPU／4 GB production Go。
- 不改变 StateGraph 节点／边、Qdrant collection、混合召回、切片、索引 Worker、readiness 探针／签发流程、prompt 注入分类器、结构化输出 schema、2 元 Chat 日上限、Embedding 预算、限流、并发、session TTL 或既有机器码；本任务修改的 estimator／policy version 必须自然使旧 readiness receipt 失配，但不新增 receipt 类型或在线探针。
- 不摄入 About 模板静态文案，不增加联网搜索、JD 匹配、测评、工具调用、跨 session 记忆、分析、通知或原始问答日志。
- 不迁移内容事实库、不修改 LangGraph Saver 固定表、不引入第二 runtime owner，也不在本阶段把 SQLite checkpointer 改为 Postgres。若现有 control schema 无法原子表达 captured execution identity 或可重试清理事实，只允许增加这些事实所需的最小、前向兼容 runtime control migration；不得借机增加产品能力。未来需要多 API 进程或共享存储时必须另建持久化迁移 spec。
- 不改写或删除第三阶段 archive、evidence 与 event；只在新决策和发布文档中记录本次复核结论及生产 No-Go。

# Acceptance criteria

- AC-1: 每个正常或恢复 runner 都持有不可变 execution identity：`session_id`、准入时的 `fencing_epoch`、`turn_id`、`thread_id` 和本次 session／IP／global 三条 lease 共用的 `fencing_token`。normal mutation permit 必须在一个短 control 事务内验证 session 未 tombstone 且未过期、epoch 精确匹配、turn 属于该 session 且状态为 `accepted|running`、三条 lease 的 owner／token／有效期全部匹配；只检查“session 还活着”不合格。prepared turn 重启只能在同一事务重新竞争三条 lease、取得 fresh token 并把新 identity 交给 graph；sending／unknown attempt 只能进入禁止 provider dispatch 的 recovery fence。checkpoint 中的旧 token／epoch 永远不能授权恢复后的 mutation；无法取得对应 fence 时不得启动 graph、Saver write 或 provider。
- AC-2: `prepared→sending` 是每次 query-embedding／Chat provider 调用的唯一授权线性化点，并与 AC-1 fence 在同一短事务完成。DELETE、expiry、lost lease 或 breaker 先赢时 prepared attempt 必须零调用、CAS 为既有无费用失败状态并 exactly-once 释放预留；sending 先赢时至多允许该既有一次网络调用完成或未知，失去 fence 后不得重试、创建第二 attempt 或把 provider 结果用于正文。lost-fence completion 只允许按既有价格快照 exactly-once 写入不含原文的费用与必要 allowlist usage，结果未知按既有最坏值结算；`parsed_json`、`vector_json`、答案、引用、history、event、checkpoint 和 hub delivery 均不得提交。fence 失败不能由旧 runner 补写一个看似正常的 terminal。
- AC-3: stage event、terminal、history 和 live publish 对同一 session 服从一个 per-session async serialization boundary。stage 事务只幂等插入 journal；terminal 事务原子写 terminal、对应 journal 与成功 answer history。两类事务都只在真实插入时返回绑定 execution identity、event seq 和 terminal 状态的一次性 publish receipt，重复节点返回 no-op receipt。receipt 在同一 serialization boundary 内、hub publish 前再次验证，DELETE／epoch 变化先赢时关闭旧 stream 并使 receipt 失效，terminal 先赢时也不得让 DELETE 返回后继续发送正文。cleanup／recovery 只能用独立的 no-body recovery permit 写安全终态，不能借该 permit 发送 provider、保存原文或绕过 AC-2。任何 `terminal-commit→DELETE→publish` 顺序最终都只有一个可观察终态，DELETE 确认后零迟到 event／正文 delivery。
- AC-4: 项目提供 identity-aware Saver adapter 包裹 pinned `AsyncSqliteSaver`，不 patch site-packages、不替换 Saver 固定表，也不信任 `aput()` 返回 config 保留自定义 configurable 字段。adapter 以服务端 `thread_id→execution identity` 绑定和 AC-3 同一 per-session serialization boundary 执行“短 control fence check → underlying Saver write／commit”；DELETE／expiry 取得同一 boundary 后再 tombstone，禁止 `checkpoint-check→DELETE→commit` TOCTOU。control 数据库事务不得跨 Saver `await` 保持打开。checkpoint state 只保存 current question、内部 ID、generation／published-version 绑定、evidence ID／alias／path 等 descriptor 和必要非正文恢复状态；不得保存 hydrated evidence body、历史正文、query vector、provider raw response、parsed／terminal answer。需要 evidence 的节点临时从当前公开投影 hydration，并在模型调用前和 terminal commit 前复查 descriptor 仍绑定同一公开版本；失效时丢弃结果且不得再次调用模型。
- AC-5: `runner_quiescent_at` 只证明 runner 已停止；`checkpoint_deleted_at` 只在 `adelete_thread(thread_id)` 成功且独立复查 `checkpoints`／`writes` 为零后写入。Saver 删除必须 awaited、可观察、可重试，禁止 fire-and-forget；Saver 或零残留复查失败时 checkpoint marker 保持 null、记录 retry fact 并打开 cleanup breaker。SQLite FK、48 小时行删除或 WAL checkpoint／truncate 失败同样记录 retry fact 并打开全局 breaker，但不能清空、延迟或伪造已经真实成立的 checkpoint marker；`allow_wal_truncate=false` 也不影响 marker 语义。breaker 阻止新 session、新 idempotency key 与 provider dispatch，existing GET／DELETE／replay／attempt settlement／cleanup 继续受 envelope 约束而可用。
- AC-6: query `vector_json` 在 dense candidate／degraded fact 确定后立即删除，Chat `parsed_json` 在 terminal 成功提交后立即删除，验证失败的 parsed result 在下一 attempt 创建前删除；这两个 transient raw 正常路径不得等待 sweep。公开/API 可读正文硬上限由 policy 的 `body_retention_seconds` 表达，默认 900 秒且可因 256 KiB cap 更早结束；到达 `terminal_at + retention` 后，session view 不依赖物理清理 marker 即返回 `body_available=false` 并不序列化 question／answer／message／citations／sources。物理 purge 在同一 900 秒内清除 turn、journal、history、attempt raw 与 Saver 原文是 SLA；失败 residue 仍不可公开读取，marker 不伪造，立即开 breaker 并禁止生成更多原文。raw-byte 统计按 UTF-8 bytes 覆盖 admission question、event journal、attempt raw、terminal／history、checkpoint／writes，并在 admission 及每个对应增量 commit 后重算；查询失败时保留最后一次非负 `persisted_bytes`、设置 session/global cleanup breaker 作为权威 unknown，任何消费者不得把 last-known 当当前值或把错误按 0 字节处理。超限后循环清最旧 terminal；单 active turn 仍超限时先失效 lease／Saver permit，再清原文、按 AC-2 结算，并复用 `provider_result_unknown` + generic message 安全终结。`body_purged_at + 48h` 后仅在 attempt 已结算且 Saver 零残留时按外键顺序删除 per-turn／session 最小记录。
- AC-7: browser document controller 为 bootstrap、stream、status GET、polling 与 DELETE 使用同一单调 generation。确认清除时在发请求前递增 generation、停止 timer、abort 全部旧 fetch／stream、解绑 listener，并清除 draft、transcript、stage、key、payload、cursor 及其他原始内存；每个 async callback 在写 Vue state 或新建 timer 前验证捕获 generation。204 只说明“本站可读正文与引用已清除，最小费用记录最多保留 48 小时”；202 只说明“旧会话清除已发起且后台仍在完成”；网络失败只说明“本地视图已清，服务端清理状态未知”。三种结果都不得恢复缓存正文、自动 bootstrap／重问或宣称撤回供应商数据；DELETE 前发出的 GET／SSE 在任一结果之后到达也不能复活旧内容。
- AC-8: 每个助手 fetch 设置 `redirect="error"`，并要求最终 `response.url` 的 origin、pathname 与目标 endpoint 精确相等且 `search==""`、`hash==""`；额外前后缀、重复斜线、encoded separator、query、跨源或 redirect 均失败，禁止 `endsWith()`。GET hydration／polling 的 completed answer 在进入 Vue state 前必须经过与 SSE 相同的 body／marker／citation／source／navigable-path 字段 allowlist 和闭包；失败时隐藏整份答案，未经验证的 path 不得进入 `NuxtLink`。应用不使用浏览器存储，textarea 无 `name` 且 `autocomplete="off"`，并在 `pagehide`／BFCache `pageshow.persisted` 主动清原始内存；只对项目注册的受支持浏览器作可验证承诺。普通 transport 断开最多两次使用原 key／payload 重连，SSE 协议错误不得自动重问。正常 `200 + active_turn` 且无 `Retry-After` 时按基础 3 秒继续 GET，terminal 停止；仅 429／503 等等待响应可用合法 1–86400 秒 header 覆盖下次延迟，header 缺失／非法时停止自动请求并显示人工刷新。180 秒 horizon 从首次 polling 起累计，recovery 全程保持 submit lock。
- AC-9: `<1280px` 的公开导航 modal 与助手只允许一个 overlay owner。打开任一浮层时先以 `restoreFocus=false` 原子释放另一方，再由新 owner 取得 inert、scroll lock、focus；隐藏助手不取消后台 turn。390px、639px、640px、1024px 及跨断点变化不得出现两个 `aria-modal=true` dialog、双 focus trap、残留 inert／body lock。桌面外部元素持有焦点时缩到 639px，焦点必须进入真实可聚焦的 dialog 控件。只有 launcher 仍挂载且用户普通关闭时才还焦点；来源点击或路由导航不还旧 launcher，而把焦点移到新页面 `main`／首个 H1。enabled-state component 和 Playwright axe 覆盖双向 handoff、Tab／Escape、断点切换与 reduced-motion。
- AC-10: `/api/v1/assistant/questions` 的缺失／错误 header、畸形 JSON、错误字段类型、空白／越界 question、非法 `current_path` 和未知字段全部由 assistant 作用域验证边界翻译成严格 `400` + `ErrorEnvelope { error: { code: "invalid_request", message } }`；不得暴露 FastAPI `HTTPValidationError`、字段位置或默认 422，其他既有状态与机器码不变。`packages/contracts/openapi.json` 对该 operation 不再声明 422，并与 route header metadata、Web 类型及严格客户端解析同步；不删除其他 endpoint 的既有 422。API contract tests 逐类验证 status、Content-Type、16 KiB error-body 上限、字段 allowlist 与 `Cache-Control: no-store`，不能只验证 schema 名称存在。
- AC-11: 生成模型实际接收同一 active session 最近最多 4 个完整、未 purge 的成功 question／answer pair，按时间正序并与 current question／evidence 分区；`assistant_history_turns` 默认 4 且配置验证收紧为 `le=4`，大于 4 在 runtime validation／readiness fail closed。历史与 evidence 都以明确 delimiter 包装为 untrusted data，转义可破坏边界的内容，不能覆盖 system scope、工具禁用、引用或注入防护；DELETE、过期、跨 session、refusal／error、已 purge 正文不进入 prompt、checkpoint 或日志。项目使用版本化的保守 deterministic estimator 计算 system、structured-output schema、current question、evidence、完整 history pair 与 output/context reserve；估算值取“UTF-8 byte length + 固定结构开销”和 provider adapter tokenizer 结果中的较大值，estimator version 进入既有 assistant policy／readiness fingerprint。先从最旧完整 history pair 丢弃，仍不能证明 fit 时不调用模型；不得用字符数冒充精确 token。离线 provider capture 覆盖两轮指代、四轮上限、预算裁剪、历史 prompt injection 及 purge／DELETE 排除。
- AC-12: API 测试删除 `or True`、`x in {True, False}`、不可达 `if False` 等恒真／无效断言，以命名明确的 scenario × applicable-invariants 矩阵替代；不适用项显式 N/A，禁止用无意义断言凑齐统一列。确定性 barrier 至少覆盖 delete-before/after-sending、lease expiry、late completion、terminal-commit→DELETE→publish、checkpoint-check→DELETE→commit、prepared fresh-fence recovery、sending zero-dispatch recovery、descriptor checkpoint 零正文、Saver／FK／WAL failure、startup overdue、跨 900 秒不可读与恢复清理、48 小时 purge、中文多表 256 KiB、admission 临界值和 single-active oversize。适用场景必须断言 provider call count、attempt／reservation、正文／event／history／checkpoint／hub 迟到集合和 breaker；若有最小 runtime control migration，还须覆盖 fresh provision、上一版本 upgrade、schema fingerprint 与 Saver 表不变。
- AC-13: Web unit/component tests 使用受控时钟、可取消 fetch 与延迟 response barrier 覆盖 stream／status generation、正常 polling、Retry-After、两次重连、submit lock、hydrated citation/path 伪造、URL drift、BFCache、DELETE 204／202／unknown 和 overlay focus。assistant Playwright 在独占临时 content/runtime、Qdrant-local 与 deterministic provider 下，至少验证 active turn 完成前 reload、增量 SSE、同 key 恢复、`pause old GET/SSE → DELETE → release` 后 DOM／Vue 零复活、来源导航、多轮指代、双 overlay、键盘和 axe；不得以答案完成后 reload 或固定 sleep 代替竞态。根 `npm run test:e2e` 和 release bundle 必须实际注册并执行这些场景，自动化不访问公网。
- AC-14: 长期文档明确区分三层事实：第三阶段 Harness 形式关闭及历史 evidence 保留；本任务补齐已发现的运行时／浏览器语义缺口；真实供应商、代理、备份恢复、目标服务器与公网安全仍是 production No-Go。架构记录单 API owner、identity-aware Saver adapter、descriptor-only checkpoint、marker 事实语义、lost-fence 仅允许无原文结算和 SQLite saver 的多进程限制；产品／Web／API／Contracts 同步多轮、删除、400 与默认关闭行为。路线记录管理员运营控制面在本任务之后独立设计，生产资格再其后验收；不得把本地 `quality:release` 或本任务 evidence 写成已上线、已合并或 production-ready。

# Risks

- `AsyncSqliteSaver` 使用独立连接，若为 fencing 或删除复查持有长事务，可能造成 SQLite lock inversion。实现必须把 control 事务保持短小，不在其中等待 provider／网络，并用受控 barrier 证明顺序而不是扩大全局锁。
- provider dispatch 一旦成功越过 `prepared→sending` 就不能依赖客户端 abort 撤回；lost-fence 仍可能产生一次真实费用。本任务保护的是“不重试、不再暴露或保留正文”，不是虚构取消能力。
- 清理统计从 fail-open 改为 fail-closed 会提高暂时不可用概率，但这是 256 KiB 与 15 分钟隐私上界可信的必要代价；运维控制面必须在后续阶段展示 breaker，而不能在本阶段用日志代替状态。
- 把最近历史真正加入 prompt 会增加 token 成本和间接 prompt injection 面。完整 pair 裁剪、untrusted 分区、既有 residual guard 和离线恶意历史测试必须一起成立，不能只拼接字符串。
- SQLite checkpointer 在官方指导中不是多进程生产首选。本任务只修复当前单 owner 边界的语义正确性；生产是否迁移 Postgres 必须结合部署拓扑和目标服务器资源另行决策。
- 修复历史测试可能使本地 gate 首次暴露更多既有缺陷。不能通过放宽断言、删除场景或只更新 evidence 消除失败，必须把失败归因到具体 AC。

# Verification plan

- api-lint => AC-10
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-10, AC-11, AC-12
- web-quality => AC-7, AC-8, AC-9, AC-10, AC-11, AC-13
- e2e => AC-7, AC-8, AC-9, AC-11, AC-13
- harness-integrity => AC-14
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14
