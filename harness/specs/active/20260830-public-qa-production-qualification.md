---
id: spec-20260830-public-qa-production-qualification
level: L1
summary: 用真实供应商、目标主机和可恢复基础设施证据判定公开问答是否具备生产放行资格
load_when:
  - task:20260830-public-qa-production-qualification
author: Gavin
task_id: 20260830-public-qa-production-qualification
verification_profile: release
verification_escalation: 本任务跨越真实云端供应商、公网 TLS／SSE、可信代理、Qdrant 持久化、备份恢复和 2 vCPU／4 GB 目标机资源边界，关闭前必须运行完整 release、E2E 与脱敏目标环境资格证据校验。
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - apps/web/README.md
  - harness/docs/product/brief.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/operations/release-readiness.md
  - harness/docs/decisions/20260830-public-qa-production-qualification.md
documentation_reason: 本任务首次固定公开问答的实际生产拓扑、供应商合同、代理与存储恢复边界，并形成可审计的 Go／No-Go 结论，必须同步项目、应用、产品、架构、运维和持久决策文档。
status: frozen
frozen_at: 2026-08-31T12:46:40.562819+00:00
freeze_reason: AC-7 已对齐已交付 checkpoint 合同；管理员仍未选择生产 profile、平台、供应商与目标环境，继续冻结。
frozen_scope_sha256: 3f463cc33f22989c8602e2fc7d7b44fb207bdd6221b4a1409ecab0c4bc8e9ca9
state_history:
  - {"action":"freeze","at":"2026-08-30T12:49:08.333510+00:00","reason":"当前处于功能开发阶段；管理员明确禁止进入真实服务器、真实域名与真实供应商部署，生产资格待部署阶段再恢复。","scope_sha256":"662484443c0b71bc3e46d3f4addb8b99ea32e57f65566ddaa125af90480a8bc5"}
  - {"action":"resume","at":"2026-08-31T12:45:54.170649+00:00","reason":"文档漂移复核确认 AC-7 与已交付 checkpoint 合同冲突；仅恢复以纠正验收措辞，不启动生产资格。"}
  - {"action":"freeze","at":"2026-08-31T12:46:40.562819+00:00","reason":"AC-7 已对齐已交付 checkpoint 合同；管理员仍未选择生产 profile、平台、供应商与目标环境，继续冻结。","scope_sha256":"3f463cc33f22989c8602e2fc7d7b44fb207bdd6221b4a1409ecab0c4bc8e9ca9"}
---

# Context

公开问答已经完成第一阶段 Qdrant RAG 索引、第二阶段 LangChain／LangGraph 在线内核、第三阶段全站悬浮气泡、第四阶段运行时完整性及其 remediation、第五阶段单管理员运营控制面。第五阶段已通过 Harness 关闭，但它明确留下 production No-Go：当前 release gate、替身供应商、管理页被动状态和 readiness receipt 只能证明仓库内合同与本地行为，不能证明真实供应商、公网代理链、持久化、恢复或 2 vCPU／4 GB 主机能够安全运行。

已确认的产品边界不再重开：本站只有管理员登录；匿名助手只帮助 HR 等访客了解本站已发布内容和作者会什么，不做 JD 匹配、候选人评分或能力测评；使用云端 API key，不部署本地模型；公开 Chat 新调用按北京时间受人民币 2 元日 cap 约束，query Embedding 与 index Embedding 使用各自独立 cap；不再设置“每会话 10 问”产品额度；全局最多 3 个并发 provider lease、每分钟问题限流、30 分钟空闲和 24 小时绝对会话寿命保持不变；任何截断、无效结构或不完整终态都不能向 HR 输出半段答案。目标主机已确认是单台 2 vCPU／4 GB，运行 Nuxt、单 FastAPI API owner、单轻量索引 Worker 和独立单节点 Qdrant。

尚未确认且不能由实现者猜测的是具体生产环境：服务器 OS、容器或 systemd、反向代理／CDN、域名与 DNS、Chat／Embedding 供应商及最终模型、Qdrant server 版本、媒体 backend 与卷路径、备份目的地、RPO／RTO、保留期、告警渠道、资源／延迟阈值、证据有效期、管理员／Session／CSRF secret source、主机时钟同步、供应商数据保留与地域条款，以及 CSP 从 Report-Only 转为强制还是接受有期限的残余风险。本阶段把这些值变成部署前必填的资格 profile；任何 unknown、占位值或未批准阈值都必须保持生产 No-Go 且不能关闭本资格任务，而不是生成一套虚构部署方案。

现状还有必须由本阶段验证并在必要时收敛的生产边界缺口：真实 provider 的 readiness probe 当前被命令显式拒绝；Embedding provider 缺失 usage 时会以文本长度启发式数值冒充已知 Token，并以配置值冒充供应商返回的模型身份；Nuxt 助手代理没有建立可信客户端 IP 传递链；SSE 只设置禁止 Nginx 缓冲的提示头，不能证明最终边缘在模型静默期不会缓存或超时；Qdrant 只有客户端配置，没有固定 server artifact、私网暴露、持久卷、重启或丢库恢复证据；现有 backup helper 不执行真实一致性备份。上述问题可以在本阶段按最小生产边界修复，但不得借机重写 RAG、LangGraph 或产品能力。

# Goal

为公开问答交付一次可复查的生产资格闭环：先由管理员填写并确认非秘密资格 profile，再为该 profile 中唯一选定的平台生成可复现、最小权限且默认关闭的部署配置；用最终真实 Chat／Embedding、私有 Qdrant、真实 HTTPS 同源代理和目标 2 vCPU／4 GB 主机执行费用受控的合同、安全、恢复、资源和暗发布演练；最后生成绑定源码 commit、部署 artifact、配置 fingerprint 与原始产物哈希的脱敏资格 manifest，并由管理员作出明确 Go／No-Go 决策。

资格状态固定为 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO`；只有仍新鲜的 `QUALIFICATION_GO_CANDIDATE` 才允许任务外继续到 `FINAL_GO → PUBLIC_ENABLED`，`QUALIFICATION_NO_GO` 只能进入 remediation／重新资格。本任务的 close 只对应一次真实目标环境证据完整的 `QUALIFICATION_*`：实测 blocker 可以得到 `QUALIFICATION_NO_GO` 并关闭本阶段，随后另建 remediation／重新资格任务；缺少目标机、最终供应商、必测事实或证据完整性则不是有效 No-Go，而是本 Spec 仍未完成。`QUALIFICATION_GO_CANDIDATE` 只表示该候选版本在已记录环境中具备放行资格，不等于管理员已经作出任务外的 `FINAL_GO`，更不等于对公网永久开放。任务实施、验证和关闭全过程都必须保持 Web launcher、API capability 与 runtime gate 默认关闭；暗发布窗口结束后恢复关闭。永久向访客启用必须在所有证据仍新鲜时由管理员另行显式执行，不能由 Harness close、部署脚本、readiness probe 或资格 runner 自动触发。

# Non-goals

- 不比较多个供应商或模型，不做 LLM-as-judge、排行榜、泛化回答质量评分、训练或微调；只验证最终选定供应商与本站固定系统合同是否兼容、安全、可计费和可恢复。
- 不新增网页搜索、工具调用、写操作、管理员数据读取、跨会话记忆、JD 匹配、候选人评分或能力测评；语料仍只来自既定已发布文章、项目、读书笔记和 Profile 投影。
- 不改变人民币 2 元 Chat 日 cap、query／index 独立 cap、服务端限流、最大 3 并发、30 分钟空闲／24 小时绝对过期、无部分答案和 prompt injection 防护边界；资格调用若需要额外费用，必须先获得独立、明确且有上限的管理员授权，否则只能在现有账本内跨北京时间日完成。
- 不因为 LangGraph 官方将 SQLite checkpointer定位为本地／轻量选择而直接迁移数据库。当前 AsyncSqliteSaver 仅作为单 API owner、短匿名会话、本地持久磁盘的受限生产例外接受；例外验收失败时保持 No-Go，并创建独立迁移 Spec 评估 Postgres 或应用快照表。
- 不引入第二 API 进程、多主机、Redis、HA Qdrant、托管 LangSmith 原文 tracing 或本地模型；不把高可用伪装成单机可恢复性。
- 不预先选择用户尚未确认的 OS、进程管理器、反向代理、CDN、域名、供应商、模型、告警或备份产品；profile 未完成前不得创建互相竞争的多套部署资产。
- 不扩写 provider 适配层；当前只接受既有 OpenAI-compatible Chat Completions／Embeddings 边界。最终供应商若不满足该合同，应判定 No-Go 并另建适配 Spec，而不是在生产资格任务中悄悄增加新协议。
- 不把目标机重型日志、原问题／答案、检索正文、原始 IP、API key、secret fingerprint、私有 endpoint、provider raw response、checkpoint 或数据库副本提交 Git。
- 不在本任务结束时自动生产启用；也不因本地 release、占位 manifest、一次 readiness receipt 或管理页显示 healthy 而宣称 production-ready。

# Acceptance criteria

以下 AC 验收的是“资格控制已实现、规定事实已在真实目标环境执行或被安全 blocker 确定阻断、分类与证据可信、系统保持关闭”，而不是强迫每项测量都得到通过值。`pass` 可汇总为 `QUALIFICATION_GO_CANDIDATE`；真实测得的 `fail` 或由该 fail 唯一导致的 `blocked_by:<case_id>` 汇总为 `QUALIFICATION_NO_GO`，仍可完成本阶段并把修复转入独立 Spec。`missing`、`unknown`、`stale`、占位目标、没有真实 target/provider 或无法证明的跳过都不能关闭本任务。

- AC-1: 建立严格、版本化且非秘密的 production qualification profile schema 与校验入口。profile 在任何部署或真实 provider 调用前要求管理员填写并确认：目标 OS／运行与进程管理方式、唯一反向代理／CDN、域名／TLS／canonical origin／可信代理 CIDR 与客户端 IP 头；Nuxt、单 API、单 Worker、Qdrant 的 artifact 版本或 digest、用户、端口、启动顺序、graceful shutdown、卷和本地文件系统；当前 local media adapter 或已存在的受支持 backend；最终 OpenAI-compatible Chat／Embedding provider、HTTPS endpoint 引用、模型／版本、Embedding 维度、context／input／output 上限、timeout、batch／concurrency、usage 与 finish-reason 能力、整数 micro-CNY 价格和三类预算；Qdrant server 版本、认证、collection／volume；备份目的地、加密、频率、保留期、RPO／RTO；资源／延迟／soak 阈值、阈值依据与测试流量；证据 TTL／失效路径；资格隔离目录／卷／端口；告警渠道；管理员密码、Session、CSRF、readiness 与 qualification signing key 的 secret source／轮换；NTP／时钟漂移上限；供应商数据保留、地域、访客披露和 CSP 处置。秘密只允许通过命名 secret source 注入，不得写值。schema 除非满足 provider timeout + cleanup／settlement margin <= runner horizon < edge total／request timeout、heartbeat interval < edge idle timeout、备份与重建空间低于批准磁盘水位、soak 覆盖 profile 声明的完整工作循环等关系约束并有管理员批准的阈值依据，否则拒绝自欺性门槛。空值、示例域名、`latest`、浮动版本、未确认阈值、未知价格／维度／文件系统或缺少风险处置都必须在零部署、零 provider call 前稳定失败并保持三开关关闭；校验成功产生可复现的 profile digest，后续任何相关漂移都会使资格 manifest 和 readiness 失效。

- AC-2: profile 选定平台后，只交付一套可从干净检出复现的目标拓扑和完整配置合同：同一 2 vCPU／4 GB 主机上的 Nuxt、恰好一个 FastAPI／Uvicorn API owner、恰好一个 fenced index Worker、独立单节点 Qdrant；API 与 Qdrant 只监听回环或明确私网，公网只开放 profile 批准的边缘端口，浏览器永不直连二者或模型供应商。部署 artifact 固定依赖、Qdrant server 与基础镜像／包版本，记录 digest、非 root／最小权限、端口、卷、健康／启动依赖、优雅停机和重启策略；content SQLite、assistant runtime 与 Qdrant 使用明确的本地持久磁盘路径，runtime 能跨普通进程／主机重启保留当日账本但继续排除长期备份。媒体服从 profile 选定的现有 backend：选择 local adapter 时使用持久卷，选择仓库尚不支持的对象存储时必须得到 `QUALIFICATION_NO_GO` 并另建适配 Spec，不能在本阶段暗中扩展存储架构。API／Web env example 与启动校验覆盖当前遗漏的 provider、model/version、dimension、price、三预算、管理员／Session／CSRF／readiness secret source、origin、trusted proxy、timeout、volume 和时钟同步等生产必填项；能力开启时缺值 fail fast。secret 不进入 Git、镜像层、进程命令行、日志或 evidence，随机管理员凭据和所有 secret 的轮换步骤可演练；未选择平台时本 AC 不允许用通用占位文件冒充完成。

- AC-3: 提供只能由管理员显式执行、默认零调用且有费用上限的真实供应商资格流程；管理页 GET、应用启动、普通 health 和部署不得隐式探活。最终供应商必须满足既有 OpenAI-compatible Chat Completions／Embeddings 合同，否则记录 measured fail 并转独立适配 Spec。流程在 profile 声明的最大 calls／micro-CNY 内，通过既有权威账本或另行书面批准的独立 qualification envelope 逐次计量并记录北京时间日期，验证最终 Chat 的严格结构化输出、schema、可由响应或供应商版本化合同证明的模型／版本身份、input／output／context cap、finish reason、可证实 usage、超时和错误语义，以及最终 Embedding 的非空有限向量、实际维度、批次限制、模型身份和可证实 usage。供应商未返回 usage 时，Token 事实必须标为 unknown、按已确认策略保守结算／打开相应 circuit，并把对应资格 case 确定记录为 measured fail，不能再把 `len(text)/4` 显示成供应商事实；模型身份若不能由响应或版本化供应商合同证明则资格 case 同样失败，配置值只能标为 operator declaration；维度、模型、endpoint、价格或 capability 漂移必须阻止签发 receipt。probe 只保存 allowlisted 合同结果和费用，不保存 key、请求／响应正文或 raw provider payload；它验证兼容性而不进行多模型测评。

- AC-4: 在 profile 的真实域名与最终 HTTPS edge 上验证 browser → edge → Nuxt/Nitro → FastAPI 的同源安全与流式合同。边缘必须终止有效 TLS，正确设置 Secure Cookie、精确 origin／CORS、canonical URL、HSTS 及既有 CSP Report-Only、frame、nosniff、referrer 和 permissions headers；强制 CSP 或有期限风险接受必须与 profile 一致且不可把 Report-Only 写成已执行。公网边缘清洗所有访客可伪造的 forwarding headers，Nuxt 只从受信 peer 解析客户端地址并向 API 传递专用、不可由浏览器直写的身份，API 只信任 Nuxt peer；至少用两个来源地址、伪造 X-Forwarded-For、缺头和多级代理证明 per-IP rate limit 既不把全部访客合并为回环地址，也不能被 spoof 绕过。最终代理链关闭 SSE 缓冲，连接／idle timeout 覆盖配置的 runner 最大静默区间，并用 heartbeat comment 或等价不改变用户合同的机制保持连接；实测 stage 在 terminal 前增量到达、terminal 恰好一次、断线后同 idempotency key 不重复 provider call／收费。provider 截断、invalid schema、`finish_reason=length`、代理中断或终态缺失只能整体丢弃并返回稳定失败／完整重试语义，绝不向 HR 交付半段答案或无完整引用的正文。

- AC-5: Qdrant 按 profile 固定 server version／artifact digest、请求 timeout、认证 secret、collection 参数、最小 payload、持久 SSD volume、资源限制和磁盘水位；只绑定回环／受控私网，若流量离开同机可信边界则启用 TLS，任何公网端口或无 API key 状态都立即 No-Go。以真实 embedding dimension、distance、point／payload schema 和代表性语料验证 active generation；Qdrant 进程与整机重启后 pointer／generation 可继续读取，旧 revision、已删除／转私有内容及 lost-fence 写始终不具备检索资格。Qdrant 仍是 derived store：丢失后必须先关闭问答，再通过受 index budget 约束的 Worker 重建并 finalize；若实测重建无法满足 profile RTO，则同阶段必须启用并演练 Qdrant snapshot 恢复，否则 No-Go。容量结论只能来自实际向量维度、point／payload 数量、segment 行为、磁盘和峰值测量，不能从“4 GB 应该够”推断。

- AC-6: 实现并演练可执行的备份、恢复和上一版本回滚，不以声明性 helper 或普通文件复制代替。备份必须通过共同写 fence／受控 quiesce、支持 SQLite 与媒体一致性的原子卷快照，或经过验证的版本化 media manifest 协议，消除 content SQLite online backup 与并发媒体上传／删除之间的竞态；恢复点覆盖 index-embedding 账本、迁移版本、媒体清单／哈希，并有并发媒体变更测试证明不会得到数据库与对象不一致的混合时刻。按 profile 加密保存到主机故障域之外并执行频率、保留期、失败告警和过期检查。assistant runtime、WAL／SHM、LangGraph checkpoints／writes、lock 和临时 qualification artifacts 明确排除于长期备份，但普通重启所用 runtime volume 不得无声消失。在全新隔离目标上恢复内容与媒体，执行 Alembic／integrity／FTS 校验，创建空 runtime，使公开 Chat／query 至少锁到下一个北京时间零点，按 AC-5 恢复或重建 Qdrant，重新签发绑定 active generation 的 receipt 后仍保持 disabled；记录实测 RPO／RTO、数据计数、哈希、人工步骤和失败路径。上一 artifact 回滚必须保护当前副本、处理 generation／switch_pending、使用前向修复优先策略，不能默认数据库 downgrade 安全。

- AC-7: 在实际目标文件系统和单 API owner 拓扑上对 pinned AsyncSqliteSaver 生产例外做专项资格测试：拒绝 NFS／SMB／网络共享目录和第二 API owner，验证 owner lock、WAL／busy timeout、最大 3 并发 session lease、进程 crash／restart、部署重启、同 session serialization、30 分钟空闲／24 小时绝对过期、DELETE／cleanup breaker、checkpoint／writes 最终零残留，以及历史问题、历史答案、证据正文、provider raw/parsed payload 或 query vector 均不落入 State／checkpoint／writes；current question、内部 ID、generation/version 与非正文 evidence descriptor 只作为必要恢复状态持久化。测试必须覆盖 Saver／WAL／磁盘错误和 lock contention 下的 fail-closed、无部分 publish、无双调用与保守费用结算。任一第二 owner、共享文件系统、持续锁争用、残留或清理不变量失败都使资格结果为 No-Go，并产生独立 saver 迁移任务建议；不得在本 AC 内静默扩成 Postgres 或改变 LangGraph 拓扑。

- AC-8: 在同一台 2 vCPU／4 GB 目标主机、相同生产 artifact 和代表性真实语料上执行资源、容量与 soak 资格；任何阈值、soak 时长或流量模型都必须在运行前由管理员写入 profile，满足 AC-1 的关系约束并附依据，缺失后不得事后按结果移动门槛。运行前验证 NTP 同步与时钟漂移处于 profile 水位内，因为 BJT 预算、receipt freshness、TLS 和 manifest TTL 均依赖可信时间。场景至少覆盖冷启动、空闲、两位 HR 的低流量访问、最大 3 并发 SSE、Qdrant／FTS degraded、全量 rebuild 与 segment optimize 峰值、API／Worker／Qdrant 重启、备份过程和持续运行；批量负载可用确定性非计费 provider，另以 AC-3／AC-9 的有限真实 canary 校准外部延迟。每个进程记录 steady／peak RSS、CPU、swap、OOM／restart、disk I/O、磁盘增长与剩余空间、threads／file descriptors、Qdrant／FTS latency、完整 LangGraph 问答 P50／P95 和随时间增长；没有 OOM、持续 swap thrash、句柄／内存单调泄漏或突破任何已批准水位才可得到 pass，否则记录 measured fail。Qdrant 重建峰值、OS／代理余量和备份空间必须计入，不能只相加配置上限或复用已退役 Zvec 数字。

- AC-9: 建立至少 30 个固定、版本化、可重复且不含真实访客数据的最终系统 conformance cases；它们验证本站 RAG／LangGraph／prompt／provider 的发布合同，而不是比较模型或给回答打综合分。用最终模型执行的安全与语义用例可以在显式费用 envelope 内跨 BJT 日完成，但每次调用都受 AC-3 计量；离线 failure injection 使用同一 prompt、schema、graph 与 retriever 合同的确定性 adapter。用例至少覆盖本站事实／导航、技能与项目证据等级、跨文章综合、证据不足时拒答、直接与间接 prompt injection、恶意检索片段、system prompt／secret 提取、多轮污染、伪造／失效／未发布引用、generation 漂移、Qdrant 失败转 FTS、provider timeout／unknown、预算／rate／并发、断线／幂等、invalid／truncated structured response 和无部分 HR 输出。每项断言引用只指向当前已发布 allowlist 且与 evidence descriptor／generation 匹配，外部内容中的指令不获得更高优先级，系统提示、key、管理数据与未发布内容不泄漏；事实与语义部分由管理员按固定 rubric 人工复核，结构、安全、调用次数、费用和引用不变量由确定性检查判定，禁止 LLM-as-judge。最终 manifest 只记录 case ID、版本、pass／measured fail／有因果来源的 blocked_by、人工 reviewer 与安全分类，不记录 unknown 终态或真实问答正文。

- AC-10: 建立不改变 `/api/health` 进程 liveness 语义的最小生产观测和告警闭环。管理员现有 dashboard 继续只读 allowlisted 本地事实，刷新产生零 Chat、Embedding 和 Qdrant live call；主机／进程层另外观察 Nuxt、单 API、Worker owner／heartbeat、Qdrant、CPU／内存／磁盘、备份年龄与失败、restore／cleanup breaker、provider failure／unknown、三预算 circuit、5xx、SSE 中断、进程重启和 TLS／证书到期，provider account 侧账单／预算告警与本地 micro-CNY 估算明确区分。每个阻断告警都有 profile 指定的接收渠道、阈值、观察时间和一次无破坏性触发／恢复演练；unknown、stale 或告警渠道未验证不得显示 healthy。metrics、日志和告警禁止保存问题、答案、证据正文、原始 IP、credential／fingerprint、私有 endpoint 或 raw provider response，并有明确保留期。

- AC-11: 完成默认关闭且不破坏现有博客事实的暗发布、故障与撤回演练。所有 crash、WAL／磁盘错误、真实服务停启、rebuild、restore、rollback、secret rotation 和 destructive failure injection 都必须在目标主机的隔离 namespace／用户、专用端口、资格数据库／媒体副本和专用卷中执行，并验证清理后不修改真实 content SQLite、媒体、管理员 Session 或 active generation；最终 canary 只允许 request-scoped fault adapter、受控路由或非破坏性观测，不能停真实候选进程、破坏磁盘／WAL、执行真实回滚或污染现有数据。部署前及部署完成后 Web launcher、API capability 和 runtime gate 均为 off；在受 edge 限制、不会暴露给普通访客的 canary 窗口中完成迁移、FTS、Worker rebuild／finalize、真实 provider qualification、receipt 和一次管理员显式 enable，运行 HR 风格会话并以非破坏方式验证 Qdrant 不可用→FTS fallback、provider timeout／truncation、预算耗尽、SSE 断线和 cleanup／restore lock；Worker／API crash-restart、drain、上一 artifact 回滚、generation reconciliation、secret 轮换和重新部署只复用前述隔离资格环境的结果。紧急 disable 返回后没有新 session／turn／sending；已先 sending 的不可撤回调用至多一次、只做无正文保守结算，不产生答案、引用、history、checkpoint 或 live delivery；同一 idempotency key 不重复计费。窗口结束无论结果如何都恢复三开关关闭并保留 fail-closed 原因，qualification runner 不能自行重开。

- AC-12: 采用双层、不可混淆且机械接入 close 的资格证据。Harness `release`、API／Web／E2E 测试只证明仓库实现与离线不变量；profile 固定的 target runner 在真实目标机生成 canonical、脱敏紧凑 manifest，并用仅存在于批准 secret source 的 qualification private key 签名，仓库 verifier 只持有 pinned public key。最终 manifest 固定提交为 `harness/verification/qualifications/20260830-public-qa-production-qualification.json`，该目录必须纳入 Harness source fingerprint／change enforcement。该 Spec 仍 active 时的 task verify／close 以及任务外显式 final-Go qualification 命令必须在缺失、签名／schema 无效、TTL 过期、placeholder、missing／unknown／stale、无真实 target/provider、无法解释的 skip、被测 commit 不可达、artifact/profile/case-suite 漂移或被测 commit 后存在未重新资格化的 runtime／deploy 源变更时非零；实现该规则的 `harness-integrity` 与 release subsumption 中 `harness-tests` 必须证明作用域。Spec 关闭后 manifest 只作为历史证据，普通全局 Harness 继续验证 schema、签名与不可篡改绑定，但不得因 `expires_at` 自然到期永久拖垮未来本地 release；任何 `FINAL_GO`／`PUBLIC_ENABLED` 入口都必须另行重验当前源码、artifact、profile 与 freshness，过期历史 manifest 永远不能授权启用。manifest 至少绑定被测 source commit、不可变 artifact digest、profile／case-suite digest、`started_at/completed_at/expires_at`、失效路径集合、目标 2 vCPU／4 GB 与 OS 摘要、provider/model/version/dimension／price snapshot、active generation、TLS／proxy／Qdrant／Saver 结果、资源阈值与测量、备份恢复／回滚／kill-switch／告警耗时、qualification calls／费用和 operator classification。重型日志、抓包、数据库副本和报告留在受控本地／外部存储，manifest 只签名其内容哈希、保留位置类别和管理员已复核声明；仓库 gate 验证签名覆盖这些声明，但不得谎称在 detached worktree 中重新读取或重算离线 raw artifacts。Git 中不得出现 secret、raw endpoint、原始问答／证据、IP 或 raw provider response。

  所有必测 case 已得到 `pass` 或 measured `fail`，或者仅因已签名 fail 而被确定标为无环 `blocked_by:<case_id>` 时，manifest 才完整：全 pass 得到 `QUALIFICATION_GO_CANDIDATE`；任一 fail／blocked_by 得到 `QUALIFICATION_NO_GO`，记录 blocker、保持三开关 disabled，并可关闭本资格 Spec、另建 remediation 与重新资格 Spec。缺真实目标机／最终供应商、只有工具、占位 manifest、unknown／stale 或没有可验证因果的未运行 case 均不得关闭。`FINAL_GO` 与 `PUBLIC_ENABLED` 始终在本任务之外。

- AC-13: 长期文档准确记录第六阶段的选定生产 profile、单机所有权、真实 provider 合同、可信 IP／SSE、Qdrant 持久化、SQLite Saver 例外、三类费用、备份恢复、资源资格、监控和签名双层证据边界；使用唯一状态机 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO`，其中只有仍新鲜的 `QUALIFICATION_GO_CANDIDATE` 可任务外继续为 `FINAL_GO → PUBLIC_ENABLED`，`QUALIFICATION_NO_GO` 只能进入 remediation／重新资格。task close 只对应一次完整 `QUALIFICATION_*` 判定，管理员最终 Go 与实际 public enable 都是任务外的后续状态。文档必须保留前五阶段 archive／evidence 为历史事实，明确人民币 2 元不是供应商总账单保证、Qdrant 是可重建派生存储、runtime 不进长期备份、Report-Only CSP 的真实状态和剩余风险；`QUALIFICATION_NO_GO` 不得写成 production-qualified，`QUALIFICATION_GO_CANDIDATE` 也不得写成已经部署、已持续可用或已对访客开放。永久启用步骤只允许在管理员再次检查证据新鲜度后显式执行，不能成为 close 或 deploy 的副作用。

# Risks

- 最大风险是把“本地 release 通过”偷换成“生产资格通过”。Harness 在 detached worktree 中运行白名单命令，无法直接证明目标主机、真实供应商、TLS、资源或恢复事实；因此必须保留目标 runner manifest 与管理员复核层，且两层证据不能互相冒充。
- manifest 签名只能证明 pinned runner／批准密钥对一组声明负责，不能让 detached worktree凭空复算离线抓包和重型日志；管理员必须按 manifest 哈希复核原始产物。仓库公钥、verifier 或信任策略变化本身也属于资格失效路径。
- `QUALIFICATION_NO_GO` 是“资格判定闭环完成”，不是“生产资格通过”。若 archive、产品文档或后续任务把它简称为“第六阶段已上线”，会制造最危险的状态歧义；只有 `QUALIFICATION_GO_CANDIDATE` 才能进入任务外最终 Go 审批。
- 部署平台、域名、模型、价格、备份和阈值尚未由用户选择。猜测这些值会让 Spec 看似完整但不可执行；本任务选择 fail-closed profile，而不是并行维护多套未经确认的 infra。
- 2 vCPU／4 GB 是否足够不能仅凭平均内存估算。Qdrant segment optimize／rebuild、Nuxt SSR、API、Worker、OS page cache 与备份会同时制造峰值；只有代表性语料和目标机测量能支持结论。
- 真实供应商可能不返回可证实 usage、模型版本或统一 finish reason。继续用字符启发式冒充真实 Token 会污染费用与 readiness；保守 unknown／circuit 会降低可用性，但比虚假精确更安全。
- 可信客户端 IP 跨 edge、Nitro 和 API 有三段所有权；盲信浏览器头会被绕过，不传递又会把所有访客合并为同一回环 IP。必须在最终链路做 spoof 与多来源测试。
- SSE 在模型调用期间可能长时间无 data event；单个 `X-Accel-Buffering: no` 不能控制 CDN／代理 idle timeout。keepalive、总 timeout、重连幂等与“整段答案或无答案”必须一起验证。
- Qdrant 自托管默认网络安全不能由客户端 URL 校验保证；必须由实际 bind、认证、防火墙／安全组和必要 TLS 证据证明。容量也取决于向量维度、points、payload 与 segment，不接受固定内存猜测。
- content SQLite 与媒体需要一致恢复点，assistant runtime 又因匿名与隐私边界不进入长期备份。恢复后丢失当日账本时必须锁到下一 BJT 日；为了快速恢复而沿用不可信 runtime 会造成超支、残留 checkpoint 或旧 session 复活。
- LangGraph SQLite saver 的单机例外低于其官方生产 Postgres 建议的稳健性。例外只有在本地盘、单 API owner、低并发、清理与崩溃实测全部成立时才可接受；任何未来扩容都会自动越界。
- 至少 30 个 conformance cases 会产生真实费用和人工复核成本。它们可跨日执行，但不得绕开三账本或用低成本替身冒充最终 provider 安全行为；模型或 prompt 变化后证据必须失效。
- 监控若为求精确记录 raw question、answer、IP 或 provider payload，会突破已确认的匿名隐私边界；若只看进程 liveness，又会错过 stale Worker、过期备份、预算 circuit 和 SSE 失败。
- 暗发布中的 enable、回滚、generation 切换和 secret 轮换可能互相竞争。任何不确定状态都应牺牲可用性保持 disabled，不能为了完成演练自动清除 `switch_pending`、restore lock 或 cleanup breaker。
- CSP 当前是 Report-Only。若 profile 不选择强制 CSP，必须由管理员明确接受有期限的残余风险并记录补救任务；未作决定不能被隐藏在“其他安全头已通过”之后。

# Verification plan

- api-lint => AC-1, AC-2, AC-3, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12
- api-tests => AC-1, AC-2, AC-3, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12
- web-quality => AC-2, AC-4, AC-9, AC-10, AC-11
- e2e => AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12
- harness-integrity => AC-1, AC-12, AC-13
- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13
