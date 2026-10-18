---
id: archive-20260829-public-qa-runtime-integrity
level: L2
summary: 闭合公开问答在 runner fencing、Saver 清理、浏览器删除竞态与公开合同上的已知语义缺口
load_when:
  - task:20260829-public-qa-runtime-integrity
author: Gavin
task_id: 20260829-public-qa-runtime-integrity
status: compressed
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

# 20260829-public-qa-runtime-integrity

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在保持公开问答默认关闭、现有单 API owner、独立 runtime SQLite、`AsyncSqliteSaver`、LangGraph 图拓扑、RAG 索引和费用数值不变的前提下，使一次 turn 从准入、provider dispatch、checkpoint、event、terminal、publish 到删除和保留期清理都服从同一可验证的执行身份与顺序。失去 lease、session epoch 变化、DELETE、过期或 cleanup failure 后，旧 runner 只能对已经发送且结果未知的 attempt 做不含原文的保守费用结算，不能再提交正文、history、event、checkpoint 或 live delivery。

同时闭合浏览器 controller 的 DELETE generation fence、精确同源响应校验、轮询状态机、overlay ownership、稳定 400 合同和真实多轮上下文。所有修复必须由离线、确定性的 API barrier、Web 受控时钟和 Playwright 场景证明；此前的 archive 与 evidence 保持历史原样，新 evidence 只能证明本任务提交。

## Acceptance criteria

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

## Result

Verified and closed by the harness close command.

## Evidence

[20260829-public-qa-runtime-integrity.json](../../verification/evidence/20260829-public-qa-runtime-integrity.json)

Closed at 2026-08-29T13:32:51.049845+00:00.
