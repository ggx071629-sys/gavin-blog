---
id: api-boundary
level: L1
summary: FastAPI 服务的责任边界与当前本地 MVP 实现
load_when:
  - backend
  - api
  - persistence
author: Gavin
---

# API boundary

本目录是博客后端，负责内容发布、认证、搜索、媒体、数据库及问答助手。HTTP 接口由 FastAPI 提供，[Web](../web/README.md) 通过同源代理访问，[Contracts](../../packages/contracts/README.md) 保存由 API 声明导出的接口快照。问答 Worker 和本地嵌入服务归后端所有，作为独立进程运行。

## 代码与数据位置

| 路径 | 职责 |
| --- | --- |
| [app/main.py](app/main.py) / [app/routes/](app/routes/) | 应用工厂与认证、内容、管理等 HTTP 路由 |
| [app/models.py](app/models.py)、[app/db.py](app/db.py)、[app/config.py](app/config.py) | 内容模型、SQLite 连接与 Settings |
| [app/assistant/](app/assistant/) | 在线问答图、模型调用、短会话、SSE、预算与运行控制 |
| [app/assistant_index/](app/assistant_index/) | 公开来源投影、切片、FTS/向量检索、outbox 和独立 Worker |
| [app/assistant_resume/](app/assistant_resume/) | 可信简历下载、PDF 解析、版本存储与同步 |
| [app/assistant_qualification/](app/assistant_qualification/) | 供应商探测和生产资格校验 |
| [app/local_embedding/](app/local_embedding/) / [embedding_service/](embedding_service/) | 本地 E5 客户端、评估与独立模型服务 |
| [migrations/](migrations/) / [assistant_runtime_migrations/](assistant_runtime_migrations/) | 内容库 Alembic 与独立问答运行库迁移 |
| [scripts/](scripts/) / [tests/](tests/) / [evaluation/](evaluation/) | 工具命令、后端验证与评估资料 |

从 `apps/api/` 启动普通 API 时，`GAVIN_DATABASE_URL` 默认 `sqlite:///./data/gavin.db`，`GAVIN_MEDIA_ROOT` 默认 `./data/media`。内容库保存文章等发布事实、认证、关于页与简历版本、索引账本和统一预算策略；媒体文件位于配置的媒体根目录。开发真实问答还会读取 `.env.e5` 的内容库配置，不能假定所有启动模式都使用同一个 `gavin.db`。

问答运行库由 `GAVIN_ASSISTANT_RUNTIME_PATH` 配置，保存短会话、Chat/query 账本与 checkpoint，只有单 API owner 打开，Worker 不打开。根命令 `npm run dev:assistant:real` 使用 `data/assistant-local-real/assistant_runtime.db`；离线 `npm run dev:assistant` 使用临时 runtime。Qdrant 只保存可重建派生向量，位置由 URL/path 配置；本地模型位于单独模型目录。运行数据、密钥和模型不是源码，不提交 Git；runtime 保留普通重启状态，但排除于长期备份。

## 开发与文档维护

内容备份写围栏继续保护内容发布、索引管理和问答费用准入。公开与后台短会话创建、删除以及紧急停止只修改独立问答运行库，因此不等待内容围栏；认证、CSRF、会话序列化与执行撤销校验保持生效。管理快照复核开放状态的 readiness 绑定，发现漂移时按既有 blocked 转移推进版本和 epoch，必须由管理员显式重新开放。隔离 E2E 入口在同一测试索引上持续运行 Worker，并在关闭运行库前等待 Worker 退出；这不是生产多进程部署验证。

公开 `PUT /assistant/turns/{turn_id}/feedback` 只接收 value=helpful/unhelpful/null；需要原短会话 Cookie、Origin、CSRF 并计入请求频率限制，不调用模型。只能评价本会话未到期的成功回答，同 turn 覆盖或撤销；反馈保存于既有活动表，仅含 turn 标识、选择和时间，不复制正文。反馈到期沿用原回答终态后900秒，修改不续期；到期读取即隐藏，既有 sweep 物理删除，清除会话同步删除。新增阶段/原因事件由 sweep 删除7天前记录；调用费用账本沿用原规则，正文TTL不扩大。

管理快照显示当前未到期且会话有效的赞踩数量及当天阶段计数/min/max；后台错误计数非零时提示人工核查，既有 Worker/预算/清理异常提示保留。只在管理员打开/刷新页面时观察，无外部告警发送。匿名赞踩有选择偏差，不等于正确率；“正确且有帮助答案的成本”仍须由独立质量评测核对，不能用赞数作为正确答案分母。不采集评价正文、抽样正文或开启外部遥测；短留存不能用于永久事后复核。

校验失败最多进行原有第二次生成，系统只发送固定结构化 failure_type（格式、截断、结构、引用、事实支持或相关性），不回传失败正文。反馈参与同一输入预算，放不下则停止后续发送；原最坏预留、幂等与未知结果保守结算不变。收到非法格式与不支持的回答分别返回 output_invalid/output_rejected；provider_result_unknown 保留给未确认调用/运行状态，不能把模型输出失败解释为知识库缺资料。后台活动表记录 turn 关联的阶段和白名单原因，无新增正文留存；有限替身纠正成功不证明真实模型的重试收益。

阶段活动事件以 turn、阶段及生成序号关联，保存阶段耗时和 completed/terminal/error/cancelled 状态；assistant_stage 结构化日志另记候选/过滤/选中数量、索引代次、策略/估算版本及证据版本摘要，不记录问答、标题、引文或原始异常。Chat/query Embedding 的 metered event 按 attempt 保存观察到的实际调用耗时和费用；query 结算先读取 sending 快照，避免只有账本结算而没有观测事件。终态活动耗时为准入到终态的墙钟时差，后台 min/max 只汇总终态，不混入短阶段。阶段和调用耗时使用单调时钟，取消等待不等于同步供应商已停止；进程崩溃前未观测完成的调用不伪造耗时。日志持久化由既有日志配置决定，运行事件仍在 runtime，未新增正文留存或外部遥测；本机有限样例不证明生产 P50/P95/P99。

普通后端在本目录执行 `uv sync --locked --extra dev --python 3.11`、`uv run alembic upgrade head`，然后通过 `uv run uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000` 启动。配置名和默认示例见 [.env.example](.env.example)，依赖以 [pyproject.toml](pyproject.toml) 与 [uv.lock](uv.lock) 为准。迁移命令更新到当前 head，不把某次功能的历史 revision 当作升级终点；对已有数据库升级前先备份。

API 校验入口为本目录 `uv run ruff check .` 和 `uv run pytest`；跨端生成使用仓库根目录 `npm run contracts`。修改 API/schema 时同步 Contracts、Web 消费类型及实际 parser；修改来源、数据库或运行模式时同步本文相应章节。本文保留现行操作说明，阶段计划和历史测量通过 [plan-build](../../plan-build/README.md) 与证据链接追溯，不将历史“通过”当作当前运行状态。

## 公开资料完整性与证据隔离

助手概览的 `queue.failed` 仅统计未被当前索引覆盖的失败任务。管理读取会按当前公开投影核对 active 代次的模型/管线身份、完整切片及全文检索记录，并要求已切换重建或成功同步事实；缺失、版本不一致或无法确认时保留提醒，删除/清理失败也保守保留。读取仅使用本地事实，不探测模型或 Qdrant，不代表向量服务实时健康。历史同步列表保留原始失败状态、错误码和供应商状态，以 `resolved_by_current_index` 标记当前已收录并隐藏重试入口；此标记不证明旧调用费用已核清，不修改任务或账本。

相同正文重新发布时，索引worker仅在同代模型、版本、维度、pipeline与同来源切片正文完全一致的条件下，读取现有向量并校验完整payload绑定、维度和有限数值后复用；仍通过原版本/fence保护更新新版本切片、引用元数据及FTS。复用不再调用嵌入或新增费用记录。成功计算记录存在但无可复用向量时返回 `index_vectors_unavailable`，结果未确认时返回 `provider_result_unknown`，两者直接失败、不退避重试；普通暂时性故障仍按原策略重试。此修复不自动切换重建索引或改变问答开放状态。

默认检索候选从8条扩大到32条（`assistant_retrieve_limit` 可配置至128），两路检索各获取至多候选数的4倍后融合；证据组装上限从6000扩大到24000字符（`assistant_evidence_max_chars` 可配置）。这是模型调用前的资料池，不增加Chat输入或日费用上限。最终提示仍按完整切片、相关性和来源覆盖在原输入预算内选择；不能把候选上限或命中条数当作资料总数。

混合检索在验证当前公开版本后，按来源轮转选取候选：不同资料的最佳命中先获得位置，再追加同一资料的其他切片，避免单篇长文或简历占满候选上限。来源内仍保持相关性顺序，跨来源按最佳命中排序；不保证超过上限的全部资料均可枚举。传给模型的证据描述使用标题与引用别名，不提供来源路径；面向用户的来源卡片只显示标题，路径仅用于跳转。

新回答通过原有格式和引用检查后，正文中与该回答块引用证据精确绑定的来源地址（裸路径、HTTP(S) URL、查询参数及片段）转换为来源标题，再检查转换后的格式；SSE、会话恢复和新历史共用处理后的文本，引用元数据仍保留原始导航路径。不会用真实来源标题替任意未引用地址背书，也不会按斜杠全局删除教程中的 API、文件路径或更长路径。根路径 `/` 不作裸字符替换；未绑定当前引用的地址、旧会话已保存的正文不在这次自动替换范围内。提示明确历史仅作上下文，不能复述其中的来源地址或将旧回答当作事实证据；此呈现约束不构成全面提示注入防护。

收录读取全部已发布内容库记录，不依赖首页列表或网页分页；正文全量切片与每次回答的有限检索、输入预算是不同阶段。简历按全部页提取文字层，不静默截到页数或字符上限；扫描图像内的文字不在当前OCR能力范围。关于页默认模板仍需作者确认发布才能作为个人事实参与问答。

证据扫描允许HTTP(S)文档URL路径中完整的 `api_keys`、`api_key`、`secret-keys` 等管理页面名称，避免正常配置教程被误隔离。豁免不覆盖查询参数、片段、用户信息、正文中的凭据名称、实际密钥值或注入/泄密指令；教程代码只作为资料解释，不能作为助手执行指令。用户提问的前置拦截规则不变。

## 简历可信下载边界

下载模块只接受精确可信域集合和 HTTPS/443 URL；每跳拒绝私网及混合 DNS 结果并固定已验证公网地址，TLS仍验证原主机。最多3次重定向、10MiB PDF 字节；连接/读空闲5秒，网络子进程30秒总截止覆盖阻塞DNS。子进程不继承应用密钥或环境代理，错误只返回固定码。该模块由既有索引worker的首次/换址/手动刷新队列调用，不运行周期检查。标准库连接用于显式固定连接地址，不新增 HTTP 依赖。

PDF 提取使用锁定的 pypdf 6.18.0 和版本化文字管线；只接受未加密、可提取文字的最多20页PDF，保留页码，混合扫描页不静默遗漏。解析子进程15秒总截止、256MiB进程内存限额、200000字符结果上限；Windows 使用 Job Object，POSIX 使用 RLIMIT_AS，设置失败即 parser_unavailable。Python审计钩子限制解析代码的网络/SQLite/子进程/非库文件读取和文件写入，且不传入应用秘密；这不是对任意原生代码的通用沙箱承诺。提取结果进入内容SQLite版本记录，再由既有索引链路发布；失败暂停简历证据。

## 关于页问答投影

`about:1` 投影当前发布修订的介绍、能力自述、当前方向、写作主题和本站说明；只保存草稿不改变投影。修订的 `assistant_eligible` 只在主动发布/回滚时设置，默认 seed 不具备资格；迁移保守排除旧 revision 1。当前索引来源包含 article、project、book、profile、about 和 resume；about 与简历复用原有索引链路。主动发布/回滚在同一内容事务合并最新 about outbox，旧修订立即失去证据资格；索引未完成不等于已同步。初次重建枚举使用同一资格投影，复用现有切片、FTS/向量检索和证据字符预算。管理任务来源枚举接受 about；前端引用允许精确 /about，标题“关于 Gavin”；提示词接受明确自述，保留不从文章主题推断个人能力、冲突引用双方的规则。

## 账号管理后端

账号接口与安全策略见 [账号设计](../../plan-build/account-management/ACCOUNT-MANAGEMENT-DESIGN.md)。单管理员固定登录名，安全邮箱与公开 Profile 邮箱分离。密码在 `admin_credentials` 保存 Argon2id 哈希；`GAVIN_ADMIN_PASSWORD` 仍是启动必填项，但只在凭据记录不存在时初始化，已有密码不因配置改变或重启覆盖。不要通过改配置尝试重置已初始化密码。

升级前停止 API 并备份 SQLite，从 `apps/api/` 执行 `.venv/Scripts/python.exe -m alembic upgrade head`；0026–0028 创建凭据/挑战/配额并扩展会话，升级撤销旧会话。迁移不读取密码写入数据库；首次登录事务初始化。回退到 0025 会移除网页凭据并重新依赖配置，必须先停服备份、确认恢复凭据，不能作为常规密码恢复操作。

邮件配置只填本机被忽略的 `.env`：`GAVIN_ADMIN_EMAIL`、`GAVIN_SMTP_HOST`、`GAVIN_SMTP_PORT`、`GAVIN_SMTP_USERNAME`、`GAVIN_SMTP_PASSWORD`（163 客户端授权码）、`GAVIN_ACCOUNT_CODE_SECRET`（独立随机至少 32 字符）。支持同址收发；默认 `smtp.163.com:465` 使用 TLS 及证书验证，无明文降级。未配置时邮件接口 503，普通登录和终端恢复可用。验证码/授权码不得进入日志、聊天或仓库；SMTP 接受不代表收件箱已收到，隔离测试使用替身；真实邮件实投记录见 [账号验收 A4-02](../../plan-build/account-management/completed/account-verification/A4-02.md)，历史实投不保证当前 SMTP 配置仍可用。

密码修改/恢复原子撤销全部会话和验证码。新密码 15–128 字符，不 trim、不强制字符类别；旧配置密码可以迁移，改密才应用新策略。发送与核验配额持久化，服务器重启不清零；429 携带 Retry-After。验证码到期、错误、重用统一 invalid_code；邮件失败不自动重发。

应急恢复不需要邮箱：停服并备份后，从 `apps/api/` 运行 `.venv/Scripts/python.exe -m app.reset_admin_password --database <已迁移的SQLite绝对路径> --confirm-stopped`，按提示两次隐藏输入新密码。命令只接受现存数据库，不接受明文密码参数；重置后所有会话和挑战失效。仍读取同一 Settings 的固定登录名，成功后重启 API 并重新登录。此说明不是已对真实数据库执行的记录。

## 本机真实问答（阶段 F）

本机真实启动保留已保存的访客开放/关闭选择和后台试问停止状态；首次运行默认不对外开放，正常退出也不将运营开关改为关闭。启动仍检查 E5、当前索引完整性和签名模型探测凭据，需要时更新本机运行资格；不会自动重建或切换索引，也不会发送付费 Chat。运行条件失败不提供服务。

本机在切换索引后可直接点击“恢复后台试问”：已有管理员认证及 CSRF 通过后，在内容写入栅栏内核对当前索引与已签名模型探测凭据，由 API owner 更新资格并恢复试问，无需重启。恢复不开放访客入口、不清零费用、不解除清理/恢复保护；未完成切换、索引缺失、无效探测和旧 checkpoint 残留均拒绝恢复。此自动验证回调仅由真实本机启动流程注册，生产入口仍要求独立的生产资格验证。后台读取/刷新状态不触发资格签发。

回答块现在携带内部 `supports`（来源别名及正文原句）：每块只用自己的本轮有效引用，缺失、伪造、错绑或已知个人断言错配不能发布。普通内容保留自然综合，个人奖项/能力/经验年数/现职采用保守原句核对；该检查不等于通用语义保证。材料最多每块 8 项、每项 1200 字符，计入既有输入/输出预算，因此同额度可能容纳更少证据；不增加模型调用或重试额度。材料仅暂存于可恢复 attempt，授权终止时清除，不进入公开/管理载荷、SSE、历史或 checkpoint；管理引用已有 excerpt 保留。旧未完成结果缺材料按新校验失败处理，已完成旧回答不迁移。详见[支持材料决策](../../harness/docs/decisions/20260911-assistant-grounding.md)。本轮只做离线测试，不声明真实模型资格变化。

输入防护不再单凭“提示词”“越狱”或 system prompt 等话题词拒绝技术讨论；执行/泄露请求、实际凭据及原有工具边界仍受检查，匹配视图兼容全角字与零宽分隔。检索及恢复重新扫描正文、标题和 heading，生成提示排除带已知执行指令的历史对；其余历史仍只帮助指代。教程引用完整攻击句仍可能误拒，未覆盖改写仍可能漏检，过滤放行不是模型服从证据。分段提示保留自然综合、逐块引用、自述、冲突、部分回答、时间及安全格式限制；不增加外部校验服务。

高风险句核对会从所选 quote 扩回来源原文中的周围句子，避免截去同句前后的“谣言”或“未经证实”等限定；高风险短引文在原文重复出现时保守拒绝。断句仍是有限启发式，不能覆盖跨句否定或一般语义关系，自述合法改写也可能误拒；该补修不增加材料留存或外部调用。

简历在输入预算不足时按来源、版本和原页码轮转，后页的首条候选先于前页的追加切片，避免第一页占满剩余空间。项目等枚举回答应列出所给证据中全部不同条目，但必须区分局部片段支持的条目与经完整资料核实的总数；不能因片段只出现一项便声称只有一项。页码并不等于项目边界，仍不保证未检索页或超出预算的全部条目均已覆盖。

输入预算先为系统提示、问题、输出上限及结构化协议留空间。同一来源、同一版本且正文完全相同的证据去重；能容纳全部证据时保留检索排序，优先裁剪最早历史。仍超限时，在已有候选中按来源首次出现顺序轮转，逐一选择能装下的完整切片，跳过过大项并继续尝试后续项，不截断正文、不新增检索之外的事实。保留原别名、路径和版本，生成结果及已成功 attempt 的恢复只向后续校验传入选中证据，未发送的别名不可引用。所有切片均无法容纳时才保留 `input_budget_exceeded`。本策略不提高模型输入配置、每日费用或调用次数。

问答在裁剪历史、去重和有界证据选择后仍无法满足输入预算时返回 `input_budget_exceeded`，SSE 与会话恢复保留相同诊断码；本次未调用 Chat，不应通过刷新或原样重发解决。日志仅记录输入估算、输入/输出/上下文上限、证据条数和估算器版本，不记录问题、证据正文或密钥。`provider_result_unknown` 仍表示未能确认完成的回答，页面显示“回答状态未确认”，检查结果不会自动重发。输入预算与费用预算是不同限制；该诊断变更不提高额度或改变证据选取。

仓库根目录运行 `npm run dev:assistant:real`。启动器读取 `.env.e5` 的真实 E5、Qdrant 和公开内容库，以及 `.env` 的 Chat 与持久 HMAC 密钥；监听 `127.0.0.1:3101`（Web）与 `127.0.0.1:8101`（API）。原 `npm run dev:assistant` 继续运行离线模式。

前置条件：E5 8091 与 Qdrant 8092 已按本页 E5 操作说明启动；模型身份/切片 pipeline 已固定，公开内容已 rebuild 并 finalize；本机 Chat probe 已成功并签名，文件默认位于 `data/assistant-qualification/local-chat-probe.json`。probe 必须与当前配置和凭据一致、签名有效且成功。正常运行和重启不因记录单纯变旧而拒绝；启动显示最后验证时间，超过 24 小时仅作提示，不自动调用付费 Chat。缺失、畸形、签名异常、失败或未来时间仍拒绝；v2证据独立绑定token、模型、凭据和输出协议；价格与授权内日预算只做本地费用检查，readiness绑定当前费用配置并本地重签。旧v1证据需先按原配置离线转换。旧成功记录不证明供应商当前可用，问答仍受输出校验、费用和熔断控制。仅 `development` 接受本机签名路径，生产仍需要原资格 profile。完整操作、维护、实测与容量限制见 [本机真实问答交接](../../harness/docs/operations/local-real-qa.md)。

真实模式使用持久 `data/assistant-local-real/assistant_runtime.db`，退出和重启都保留费用。启动会迁移 runtime 至 v4：租约唯一键包含所属 turn，修复同 IP 两路/全局三路原本触发 500 的问题；单 session 仍限一路。迁移不改费用或 LangGraph saver 数据，降级前必须停止并排空租约。

本地 DeepSeek 使用 JSON 模式与应用严格校验；正常 `stop` 的空 `blocks` 表示证据不足，不再二次付费重试。截断、非法 JSON、未知引用仍拒绝；生产 strict-schema 路径不采用该本地空结果语义。

## Chat 私密配置

管理员填写 Key 使用原有 `apps/api/.env`，已被 Git 忽略；从 `apps/api/` 启动时 `Settings` 默认读取此文件。连接字段使用现有 `GAVIN_ASSISTANT_CHAT_PROVIDER=openai-compatible`、`GAVIN_ASSISTANT_CHAT_API_KEY`、`GAVIN_ASSISTANT_CHAT_ENDPOINT` 和 `GAVIN_ASSISTANT_CHAT_MODEL`；完整配置字段见 `.env.example`。保留原文件中的其他配置，不另建 Chat 配置文件、客户端或探测账本。现有 `providers.py` 提供 LangChain `ChatOpenAI`，`graph.py` 处理结构化回答，`assistant_qualification/provider_probe.py` 提供生产资格探测。

本机真实问答入口和联调记录已具备，见[实际接入记录](../../plan-build/assistant-upgrade/completed/assistant-upgrade-verification/Q4-03.md)；填写连接配置本身不等于启用问答或通过生产资格。显式 E5 检索命令使用 `.env.e5`，离线演示入口继续使用 test provider。

DeepSeek 模板已放在 `.env.example` 顶部，本机 `.env` 可按模板集中定义 `DEEPSEEK_API_KEY`，`GAVIN_ASSISTANT_CHAT_API_KEY=${DEEPSEEK_API_KEY}` 引用该值，现有 dotenv 加载器负责展开。按模板填写本机配置，模板中的 Key 保持空白；不要依赖行号定位配置。Base URL 与示例模型名依据 [DeepSeek 官方快速开始](https://api-docs.deepseek.com/zh-cn/)；它们不是本项目严格结构化输出已通过的声明。

## 本机 Chat 复验与账本恢复

继续使用 `scripts/run_assistant_provider_qualification.py`。以下命令从 `apps/api/` 执行；**本节提供操作能力，不代表获得任何新增付费授权**。除 `probe` 外，所有 local action 都不调用模型。生产入口和生产ledger不支持这些操作。

- Key、endpoint、模型、token/context/timeout或输出schema变化：原兼容性证据拒绝，需在明确授权范围内显式探测。当前只支持已复核的本机DeepSeek配置，未知模型/endpoint不会仅因给出授权就被接受。
- 仅价格变化、日预算在证据已批准上限内调整：检查正值/费用约束，正常启动会在需要时本地重签readiness，不触发Chat探测。日预算上调须先明确授权，再执行 `rebind-costs`；兼容性或凭据变化不能借费用重绑绕过。
- 旧v1只有混合摘要：保留原配置，使用 `--local-action migrate-evidence --source-probe <原文件> --output <新文件>` 离线转换。必须提供 `--local-chat --ledger <原账本>`；不修改原文件和完成时间。新配置不能反推旧摘要，若原配置不可得，记录阻塞并等待明确复验授权，不能伪造旧事实。

只读状态示例（不会创建或清零账本）：

```powershell
.venv/Scripts/python.exe scripts/run_assistant_provider_qualification.py --local-chat --local-action status --ledger data/assistant-qualification/local-provider-ledger.json
```

授权操作必须停止探测、设置 `GAVIN_ASSISTANT_ONLINE_ENABLED=false`，并使用同一readiness签名密钥。明确批准后才填写以下占位值：

```text
.venv/Scripts/python.exe scripts/run_assistant_provider_qualification.py --local-chat --local-action authorize --ledger <原账本> --authorization-id <唯一批准ID> --max-calls <累计调用上限> --approve-max-micro-cny <累计金额上限> --approve-daily-budget-cny <明确批准的日预算上限> --reason <批准范围与原因>
```

累计上限包含所有历史使用量，**不是新增量，也不按天清零**。例如已用2次、批准再做1次，应明确批准累计3次；若累计额度耗尽，更换ID但沿用相同上限不会获得新机会。价格变化后要再次付费探测，也需授权当前价格配置；相同ID幂等且不能修改，旧ID不能重新启用。授权导入旧ledger时将原文本、SHA-256、全部attempt与费用嵌入同一v3签名ledger，之后仍使用原路径；新授权和恢复均不删除原记录。不要把reason写成包含Key的配置转储。

`status` 给出剩余次数/金额和未恢复attempt。`sending`表示未完成，`unknown`保留未知结果的预留上限，`measured_fail`保留已测失败费用；三者都阻止后续探测。确认原探测进程退出并完成故障调查后，用 `--local-action recover --attempt-id <ID> --confirm-quiescent --reason <调查结论>` 追加恢复事实。独占锁仍会拒绝正在运行的探测。恢复不改原状态、时间或金额，未知始终按保守上限计入，不退还次数或自动调用。次数耗尽需明确累计次数上限，金额不足以预留下一次请求时需明确累计金额上限；恢复失败本身不能增加两者。在线问答runtime熔断仍按原运营流程处理，不能用探测恢复清除。

上调日预算后，使用 `--local-action rebind-costs --source-probe <有效v2证据> --output <新文件> --authorization-id <当前批准ID> --ledger <原账本> --local-chat` 离线绑定当前费用授权。它保留原始证据、完成时间和历史探测费用；不把费用审批时间当作兼容性验证时间。

只有兼容性确需重新验证且付费范围明确后，执行原 `--local-chat` 探测，补充 `--authorization-id <当前ID>`，并显式传入相同累计 `--max-calls`、`--approve-max-micro-cny` 与新的 `--output` 文件；不会覆写旧证据。探测进程崩溃留下sending时先恢复；新失败仍阻断，不自动重试。

选择新证据时，在启动环境设置 `GAVIN_ASSISTANT_LOCAL_PROBE_PATH` 为新文件绝对路径，再运行原npm/快捷入口；API脚本也支持 `--probe`。环境未设置时仍使用原默认文件。这样原证据不必覆盖或删除。新ledger需要同一readiness密钥，签名异常或未知schema应停止操作并调查；不提供重签篡改账本或任意密钥轮换的捷径。设计与边界见 [恢复决策](../../harness/docs/decisions/20260908-local-probe-recovery.md)。

## 本地真实 E5 检索（2026-09-06）

### 索引完整性与 FTS 定向补齐

FTS 身份是 `(generation_id, chunk_id)`；稳定 `chunk_id` 可在多代重复，单代更新/删除必须同时限定代次。简历旧版本清理仍逐代删除目标版本，不能误删新版本。新代构建完成、API-owner finalize 切换前以及真实开发入口开放 gate 前，必须通过逐条一致性审计。计数相同、HTTP 200 或 `retrieve.status=ok` 均不能替代完整性结果。

从 `apps/api/` 执行 `.venv/Scripts/python.exe -m app.assistant_index.maintenance --env-file .env.e5 audit`。默认只读，持内容写围栏并使用 SQLite 快照；从当前公开资料与同一切片规则独立重算预期集合，检查规范切片的缺失/额外/版本/正文，FTS 缺失/重复/额外/正文，以及全部向量的点 ID、完整 payload、维度、有限数值与集合配置。报告只包含身份和错误码；任何缺口或依赖读取失败返回非零退出码。简历预期来源不依赖已存在的索引行。

仅 FTS 有差异且公开投影、规范切片、向量均一致时，可显式执行 `.venv/Scripts/python.exe -m app.assistant_index.maintenance --env-file .env.e5 repair-fts --generation <当前代次> --backup <新的备份文件路径>`。先停止 Web/API/worker，保留 Qdrant 服务供只读核对；命令持写围栏完成 SQLite backup 与校验，再在单事务中定向修正当前代的 FTS 差异，复核失败回滚。拒绝覆盖备份、代次漂移及非 FTS 缺口；其他代次、内容、任务、费用和向量不变。重复执行使用另一个新备份路径，完整时修改集合为空。

这不是重建向量或切换代次，不调用 E5/Chat。审计会读取全部当前来源和集合向量，成本随语料增长，仅用于启动验收、构建/切换与维护，不放进每次在线问题或普通管理 GET。启动时资料尚未追平或写围栏被占用会拒绝开放；应先让独立 worker 完成已授权的增量工作并重试启动，不自动重建或绕过检查。审计证明收录和绑定一致，不承诺每个问题都能在有限检索/输入预算中覆盖全部资料。修复与真实数据证据见 [索引完整性修复计划](../../plan-build/index-integrity/PLAN.md)。

本机 Chat 适配位于现有 providers/graph 链路：`build_chat_model` 仅在 `development` 且 endpoint 精确匹配 `https://api.deepseek.com` 或其 `/v1` 路径时使用原有 `ChatOpenAI` 的 DeepSeek 传输适配。必须填写输出上限；线上回答链用 `bind_answer_model` 发送 `json_object`、`max_tokens`，显式关闭 thinking 与自动重试。schema 指令包含在输入预算估算中，完整原始 JSON 经严格类型、必填字段和禁止未知字段校验，再进入既有引用与完成原因校验。截断或解析失败也保留 usage 用于原有费用结算；未知 usage 继续保守结算。

该适配没有供应商端 strict schema 保证，只保证应用接受的结构经过严格校验；它不签发 readiness、不启用在线开关，也不绕过生产资格。生产与其他 endpoint 仍使用原有 `json_schema + strict=True`。详情见 [本机 Chat 决策](../../harness/docs/decisions/20260906-local-deepseek-chat.md)。本机真实调用、完整问答和费用验收历史见[本地问答计划](../../plan-build/local-qa/build-qa.md)。

本机探测复用 `scripts/run_assistant_provider_qualification.py`，当前授权、status、recover 与 probe 操作按[本机 Chat 复验与账本恢复](#本机-chat-复验与账本恢复)执行。须提供当前批准的 authorization-id、累计次数/金额上限及新的输出文件，不直接复用历史调用配额示例。该入口仅接受 development、在线关闭和已复核的本机配置，结果标注本机 scope 与 `production_qualified=false`；保留同一账本，不能通过删除账本刷新预算。

以下为 2026-09-06 历史测量，不构成当前费用配置或新增调用授权：当时批准E/F总计1元，Chat日上限2元；首个结构化真实请求输入207、输出17 tokens，完成原因stop，按高峰输入未命中3元/百万、输出9元/百万保守计入0.000774元。版本DeepSeek-V4-Flash-0731依据官方声明，响应仅证明模型别名。该结果不替代完整问答与资源实测，也不签发在线readiness。紧凑结果见 [本机探测manifest](../../harness/verification/evidence/20260906-local-chat-probe.benchmark.json)；本机账本及配置不提交。

独立服务归 API 所有；仅使用检索入口时不启用 Chat，真实问答使用前文的显式 real 入口，生产 gate 不自动开启。离线 `npm run dev:assistant` 不改变语义。配置与版本边界见 [E5 决策](../../harness/docs/decisions/20260906-local-e5-retrieval.md)。以下命令除 npm 外均从 `apps/api/` 执行：

1. `uv sync --locked --project embedding_service`，`python scripts/download_e5.py`。固定官方模型文件约 493 MB（不含虚拟环境），落在 `data/models/multilingual-e5-small/`；逐文件哈希不通过则不加载。
2. 在后端环境设置 `GAVIN_E5_MODEL_DIR` 为该目录绝对路径和随机 `GAVIN_E5_API_KEY`（至少 24 字符）。Windows 用 `embedding_service/.venv/Scripts/python.exe scripts/run_e5_service.py`；POSIX 使用对应 `bin/python`。loopback 端口 8091，单模型 owner；Ctrl+C 停止并等待在途推理退出。
3. 单独运行有鉴权、持久化的 Qdrant，配置 `.env.e5`（从 `.env` 复制后按 `.env.example` 的 E5 段修改）。保留 development 内容库，或通过 SQLite backup 创建独立开发快照；不要将两个开发模式同时指向同一个内容库。模型服务 secret 与客户端 embedding key 相同，Qdrant 使用独立 secret。所有 secret 放忽略配置，不能进入浏览器。
4. 根目录 `npm run dev:assistant:retrieval -- smoke`；不需要 Chat 凭据。`... -- rebuild` 输出 staging generation，`... -- finalize <generation>` 在 API owner maintenance 下完成受控切换且保持 disabled。`... -- query "作者的技术项目有哪些？"` 输出实际检索状态、版本与公开来源；不是 Chat 回答。启动后更新发布内容可使用现有 Worker `--once` 或常驻模式处理 outbox（加载同一 `.env.e5` 环境）。
5. 使用推理环境运行 `scripts/check_e5_reference.py`，核对中英文向量与官方 pooling 公式、usage。仅运行本机回归不构成服务器容量或正式人工检索验收。

服务健康是 `GET /healthz`；内部身份核验为带 Bearer Key 的 `GET /readyz`。`POST /v1/embeddings` 接受单条字符串数组、384 维和 float/base64，拒绝空白、超长和错误身份；usage 包含实际前缀及特殊 token。队列满返回 429，期限超出返回 504。服务端不记录原文或 key。更换模型/权重/切片需改变版本并重建，不能混用旧向量。回滚同样恢复配套 generation，经既有 finalize/readiness 操作且先保持 gate 关闭。

模型迁移前先用旧配置排空 active outbox，并在新 generation finalize 前暂停发布变更；发现 generation 身份不匹配时 Worker 拒绝把新模型向量写入旧集合。重复 `rebuild` 会复用已有 ready staging，必须先 finalize 才能开始下一轮。模型身份不变时，正常发布/改版/删除继续由现有 Worker 处理。

2026-09-06 检索阶段记录使用忽略配置 `.env.e5`，使用 `data/e5/content-verified.db` 独立快照、`runtime-verified.db` 和认证 Qdrant；该次实验未改动原库 `data/gavin.db`，这不描述后续运行的实际库选择。E5 端口 8091、Qdrant 端口 8092（gRPC 8093）；进程 ID 和日志在 `data/e5/`，内部 key 在忽略配置，勿输出到终端或复制到聊天。该快照不会自动同步原库新文章；完成后续部署时需对实际目标内容库重新构建索引。

本机参考误差、预热延迟、干扰测试和重启事实见 [本机测量](../../harness/verification/evidence/20260906-local-e5-retrieval.benchmark.json)。它明确不包含正式人工 Recall@5 或生产资格。若本机进程已停止，先按上面的环境变量启动 E5；Qdrant 使用 `data/qdrant-bin/v1.18.3/qdrant.exe`，设置 `QDRANT__SERVICE__HOST=127.0.0.1`、`HTTP_PORT=8092`、`GRPC_PORT=8093`（端口键同样带 `QDRANT__SERVICE__` 前缀）、`QDRANT__SERVICE__API_KEY`，以及 `QDRANT__STORAGE__STORAGE_PATH` 指向 `data/e5/qdrant` 的绝对路径。该 Windows 制品来自官方固定 v1.18.3 发布，ZIP SHA-256 为 `984619bbd4032ace578656174c465c5d6b71d1267ecad5b7b4c21cc6549ca833`。

开发部署不安装系统服务；本地模型/Qdrant 的端口、数据与日志留在忽略目录，先停进程再更换目录。本机容量评估使用完整进程组采样；历史资源报告见[容量测试](../../plan-build/capacity-tests/2c4g-retest-concurrency-rebuild.md)，不能代替实际目标环境验证。生产 HTTPS 和资格 profile 留待后续实际部署专项，E5 生产配置当前明确拒绝。

四方向本机评估入口：从 `apps/api/` 运行 `.venv/Scripts/python.exe -m app.local_embedding.evaluation --output data/e5-evaluation-new`（POSIX 用 `bin/python`）；`--review-only` 可无需服务生成复核材料。使用全新隔离数据库、两套随机前缀 Qdrant 集合和显式双语 Profile，保留原库。40 条 AI 起草正向问题及 6 条边界用例已获管理员人工审核确认，本机正向集实测 39/40。题集摘要、容量测量及下一步见 [评估操作说明](../../harness/docs/operations/e5-retrieval-evaluation.md)。已有 benchmark 保留测量时的历史状态。

容量测量入口：先在根目录 `npm run build:web`，再从 `apps/api/` 运行 `.venv/Scripts/python.exe -m app.local_embedding.capacity --output data/e5-capacity-new`。当前为 Windows collector，创建隔离五角色进程组，结束后只关闭本轮进程。实测 115 次查询成功；进程组工作集合计稳态样本中位数约 1.99 GiB、全程同步峰值约 2.13 GiB。保守规划为 7–8 GiB 内存、约 2 个同档逻辑核热态预算、应用侧约 12 GiB 磁盘（OS/未来媒体另计）。这是 41 个受控来源、1,001 切片/代及单查询并发的本机估算，不是云端保证或真实 Chat 开销。阶段 D 已完成；按管理员最新要求跳过 2 核 / 4 GB 虚拟机实验，恢复 Chat 配置准备；供应商、模型与预算待确定，Chat 尚未启用。证据见 [容量 manifest](../../harness/verification/evidence/20260906-local-capacity-measurement.benchmark.json)。

承载 FastAPI、SQLAlchemy 2.0、Alembic、SQLite FTS5、认证、媒体抽象和内容管理 API。OpenAPI 是已声明路径与 schema 的生成基线；Session Cookie、CSRF header 和非 2xx 失败语义仍以运行时依赖与路由声明为准，不能从快照缺项推断为不受约束。

## 第一阶段

当前实现文章草稿、乐观锁自动保存、发布、公开读取，以及带 CSRF 与登录限流的单管理员 Session。开发环境复制 `.env.example` 后运行 Alembic，再用 `uvicorn app.main:create_app --factory --reload` 启动服务。

运行时采用生产安全默认：API 与 Alembic 通过同一 Settings 工厂执行启动校验；管理员密码必须显式配置，生产环境要求 Secure Cookie，带凭据 CORS 不接受通配来源。所有 SQLite 应用连接启用外键约束；文章、项目和读书笔记首次发布后 slug 不可修改，以保持公开 URL 稳定。已发布正文中的 `[[wikilink]]` 与文章工作副本参考资料在发布时写入 `content_links`；公开文章上下文、项目详情和书摘详情返回最多 20 条反链，只含已发布未删除来源。

所有表示瞬间的时间在应用和 API 边界使用 UTC-aware 语义；SQLite 为兼容既有数据继续保存无偏移 UTC，读取时恢复 UTC 时区，历史无偏移值按 UTC 解释。文章和读书笔记的年月公开路径按发布时间的 UTC 年月生成。

## 第二阶段

已通过 Alembic 增加栏目、标签、项目、读书笔记及内容关联。管理 API 提供受 Session／CSRF 保护的分类 CRUD，以及项目和读书笔记的草稿、乐观锁更新与发布；公开 API 只返回已发布内容，项目关联文章也执行二次发布状态过滤。

FTS5 全站搜索现覆盖已发布文章（含栏目与标签）、项目和读书笔记。公开 `/api/v1/search` 继续只使用文档级 `search_index`，行为不变。媒体 API 通过存储协议协调本地适配器，在任何 EXIF 转置或完整像素解码前检查实际格式与产品像素上限，并把 Pillow 解压炸弹告警转为请求错误，验证后生成 WebP 与可用的 AVIF 派生文件；根目录和字节／像素限制由 `GAVIN_MEDIA_*` 配置。三类内容使用 `deleted_at` 进入统一回收站，并支持安全 YAML front matter 的 Markdown ZIP 导出与草稿导入。已发布文章的永久删除会先卸下发布修订与项目工作关联，再删除文章行；项目修订快照里的 article_id 仍是非外键整数。

本地媒体适配器把同一资产的派生文件写入唯一暂存目录后原子发布；上传事务在数据库提交前失败时回滚 Session，并按服务端随机 key 补偿删除本次文件。成功提交后不再执行补偿清理。

每个 API 实例用进程内 async 边界串行协调 HTTP mutation；进入该边界的每个请求仍独立取得并释放同一个非阻塞跨进程内容写 fence。因此，同一 API owner 的正常并发 mutation 会依次执行，不会因互相竞争文件锁误报 503；备份、恢复或其他外部 owner 已持有 fence 时，请求仍立即 fail closed，返回 `503 content writes are temporarily fenced` 与 `Retry-After: 5`，而不是等待外部操作或绕过一致性保护。异常路径同样释放进程内边界和文件 fence。

读书笔记创建与更新的 `cover_url` 接受完整 HTTP(S) URL，或媒体库返回的 `/api/v1/media/{id}/webp`、`/api/v1/media/{id}/avif`（ID 为正整数）；其他相对路径与非 HTTP(S) 协议仍被拒绝。Markdown 导入元数据暂仍只接受 HTTP(S) 封面，因此含站内封面的导出文件直接重新导入会返回 422；本轮未扩展该契约。

Markdown 导入在任何写入前验证全部文件：最多 50 个、单文件 2 MiB、批次 10 MiB、front matter 64 KiB，并限制 YAML 结构复杂度且拒绝 anchor/alias。解析前先统一 CRLF/CR 换行为 LF，使 Windows 与 Unix 换行的同一内容得到一致的元数据与正文；换行兼容不放宽 front matter、YAML 与编码校验。三类元数据使用禁止未知字段的可判别模型；整批任一文件失败时不创建部分草稿。

文章、项目、读书笔记的公开与管理列表，以及管理媒体和统一回收站，使用默认 20、最多 100 条的 `limit`/`offset` 有界查询；搜索单页最多 50 条。所有分页列表使用时间与 ID 的稳定次序，回收站在 SQL 联合查询后全局分页，关系数据在页内批量加载。

项目与读书笔记和文章一样使用 working copy + immutable publish revision：管理 PATCH 只推进工作版本，显式 publish 携带预期版本并原子切换公开快照；文章 `POST /publish` 与项目/书摘一样校验 `PublishRequest.version`。已发布 slug 不可修改。公开 API、搜索、站点地图、项目关联文章卡片与 Markdown 导出只读取当前发布 revision。公开文章的栏目与标签赋值同样来自该修订：`GET /articles` 的 `?category=` / `?tag=`、`GET /taxonomy` 计数、详情卡片栏目和搜索 taxonomy 字段都不跟随未发布 PATCH；同一栏目/标签的现场改名仍作用于仍指向它的发布修订。`GET /taxonomy` 另给 `total_article_count`，计入全部已发布未删除文章（含未分类）。

全站单例个人名片由 `profiles` 表（明确字段、版本号、时间戳）承载：公开 `GET /api/v1/profile` 按 `city_visible`/`email_visible` 从响应中移除隐藏字段，管理 `GET/PATCH /api/v1/admin/profile` 要求 Session+CSRF、校验字段长度与 URL/邮箱格式、允许可选 `website_url`（仅 HTTP/HTTPS）、允许与默认资料一致的零技能列表并以版本号乐观锁冲突返回 `409`；迁移种入 `id=1` 默认行保证首页不空白。媒体资产按 `content_sha256` 去重，并支持 `deleted_at` 软删除、逐条恢复与当前页批量 discard；编辑器内导入复用同一生命周期。

公开 `/about` 的专属文案由 `about_pages` 工作副本与 `about_page_revisions` 不可变发布修订承载：公开 `GET /api/v1/about-page` 只解析当前 `current_revision_id`，管理 `GET/PATCH /api/v1/admin/about-page` 保存草稿并推进 `version`，`POST /publish` 创建下一条修订并原子切换公开投影；修订列表、详情、按区块差异与回滚使用 `/admin/about-page/revisions*`。引言 `statement` 与 `profiles.bio` 解耦，身份卡仍由 `/profile` 提供。迁移会为既有库种入与当前页面一致的修订 #1，默认种子不具备问答资格；站长主动发布/回滚后的合格修订已进入 About 问答投影与索引链路，见上文“关于页问答投影”。

Playwright 通过 `scripts/run_e2e.py` 启动隔离 API：每次进程使用唯一的系统临时 SQLite 数据库与媒体根目录，不读取仓库内固定 E2E 数据库，也不执行持久数据库删表。

## 文章发布修订

每次普通文章发布都会创建按文章单调递增的不可变修订，并快照栏目、标签和公开参考资料。自动保存只更新工作副本；公开读取、列表、RSS、站点地图和公共 `search_index` 只投影当前发布修订。管理 API 保留修订列表、详情、差异与回滚；回滚创建来源为 `rollback` 的新修订，不改写历史，存在未发布工作副本时拒绝覆盖。

公开文章上下文、wikilink、参考资料与反链继续只基于已发布且未删除内容。文章、项目、书摘的发布／回滚／回收站／永久删除，以及会改变公开文本的栏目／标签改名和个人名片公开投影变化，会在同一 SQLite 事务中登记助手索引任务；请求路径不调用 Embedding 或 Qdrant。任务登记失败会使业务事务失败；外部索引故障只能让已提交任务重试，不能回滚已经合法的发布。

## 助手混合索引（默认关闭）

### 有限改写与显式计数摘要（2026-09-12）

支持“使用/采用/用”、已知数据库名称与“数据库”后缀、保留同一条件和次数的“在失败后再试/失败后重试”，以及数量明确且与互不重复列表项目数一致的模块/项目枚举摘要。举例、“等”、重复项、数量不一致或未声明的集合运算不推断为完整总数。

40例合成诊断不能替代真实问答质量：自由因果改写、跨集合加总及其他未知语义仍可能拒绝，相关限制在阶段计划中保留。

### 数值原位规范化（2026-09-12）

数值在完整陈述中的原位置规范化，保留对象、属性、时间、范围和上下限；不能仅凭数字集合相同通过校验。支持有限中文整数/小数、明确的毫秒/秒/分钟/小时换算、共享时间单位的“到/至”范围、百分之表达，以及成功率/占比等明确语境下具有有限十进制结果的分数。使用十进制精确运算，保留大数差异，不将循环小数近似成相同值。

月份不推定为30天，未知单位/任意算术不自动换算；分母为0的比例表达不能作为有效数值回答。该规则不负责组合计数和自由语言归纳，仍需后续正例验证。

### 有限事实与语境支持校验（2026-09-12）

普通陈述与个人/关系陈述一样必须得到当前引用语境支持；有限等价规范化保留使用/采用、技术列表和既有 About 自述/文章主题摘要。句子紧邻“上述说法不实”等撤回时，把撤回语境绑定原句；不得仅摘出前句肯定陈述。对可直接辨认的同主体“采用/使用/依赖”属性，若当前证据存在“仅/只”排他声明且值不同，或明确取消，单方陈述会拒绝；披露冲突须引用双方并呈现冲突值，不设来源类型全局优先级。普通多技术并用、双许可证或不同主体不能仅凭不同值判成冲突。

图节点把当前问题传入校验。现有确定性主题检查覆盖数据库与许可证：有依据但明显答错主题也不能作为成功答案；“材料未记载”只描述当前证据集合，已存在对应主题时不得虚报缺失。其他未知题型仍缺少独立语义相关性证明，任意中英文改写、跨文档实体消歧和隐含时间关系不在本规则保证内。拒绝得更多不代表质量更高，数量/改写与实际模型质量须分别评测。

### 当前问题与历史的检索顺序（2026-09-12）

普通查询和 E5 查询都先放当前问题，再按从近到远的顺序补入历史；当前问题先占用既有字符/token 预算，也先进入最终 FTS 的前 12 个词项。精确、宽松和旧式 MATCH 使用同一顺序，长历史不会挤掉当前短问题。当前问题本身超出词项上限仍可能截断；E5 超长问题继续显式词法降级。查询仅在节点内瞬时构造，缓存向量只在完整查询指纹相同的情况下重用。

该调整保留短指代问题的最近主题词，不提供语义消解；宽松 OR 仍可能召回旧主题。真实模型相关性和完整性另由后续质量评测确认。

### 词法投影与中文子串召回（2026-09-12）

FTS5 的 `unicode61` 会把一段连续中文当作单个词项，所以“向量检索”无法命中“系统支持全文检索和向量检索”。索引写入现在把 CJK 字符逐字分隔后存入 FTS 的 `title`、`heading_path` 与 `body`，检索依次尝试精确形式（词项之间 AND，中文按相邻字符对 OR）、宽松形式（全部词项 OR）与旧式 `safe_match_query`；精确术语、英文单词与旧式整串命中的既有行为保持不变。审计同时接受逐字投影与原始正文投影，`repair-fts` 会用同一投影写回。

已经建立的 generation 在重建前仍只有原来的召回能力：既有索引行保存的是未切分正文，中文子串要等受控重建（`--rebuild` 与 API owner finalize，或 `repair-fts`）之后才能召回。本次改动不提高输入预算、不调用新模型，也不改变全站 `/api/v1/search` 的文档级 `search_index` 行为。

这是内部检索基础，本身不等于在线问答能力或生产资格。默认关闭的公开问答 API、Web 消费层与运营面已进入当前代码，但尚未通过真实生产资格，也未向普通访客开放。未启用在线助手时，API 进程不启动 Worker、不连接 Qdrant，也不要求 runtime SQLite 或模型密钥。现有服务在没有 Qdrant、没有 `GAVIN_ASSISTANT_*` 环境变量时保持可启动、可迁移。

派生索引以 SQLite 为规范切片、助手专用 FTS5、outbox 任务和 generation 指针的事实库；Qdrant 只保存可从 SQLite 重建的稠密向量。浏览器不得直连 Qdrant。Worker 由 `apps/api` 所有，入口是 `python -m app.assistant_index.worker` 或 `scripts/run_assistant_index_worker.py`；每个进程使用唯一 owner identity，SQLite `BEGIN IMMEDIATE` 串行领取单调 fence，并在长 Embedding／Qdrant 调用中续期 owner 与 task lease。索引 Embedding 账本、持久 rebuild command／source progress 和 repair intent 位于内容事实库，Worker 绝不打开 `assistant_runtime`。

`GAVIN_ASSISTANT_INDEX_WORKER_ENABLED` 默认 false。显式启用时必须提供明确的 provider、model、model version、dimension，以及 Qdrant 配置；缺项或占位值会使 Worker readiness 失败关闭，且不得生成伪向量。production 拒绝 `test` 替身。首个真实适配边界是 OpenAI-compatible Chat Completions／Embeddings；Worker 与 query 路径使用各自账本约束的 metered Embedding。production 只接受带认证的私有 Qdrant URL，拒绝嵌入式目录。development/test 可用 `GAVIN_ASSISTANT_QDRANT_PATH` 指向进程私有的嵌入式目录；未设置 URL 或 path 时使用进程内存模式，`.`、`./` 与 `/` 等非私有路径会被拒绝。切片大小和 overlap 由 `GAVIN_ASSISTANT_CHUNK_SIZE` / `GAVIN_ASSISTANT_CHUNK_OVERLAP` 显式配置。

## 匿名公开问答内核（默认关闭）

`GAVIN_ASSISTANT_ONLINE_ENABLED` 默认 false。这是可供公开悬浮气泡消费的后端内核，仍不是对访客默认开放的产品；Web 另有 `NUXT_PUBLIC_ASSISTANT_UI_ENABLED`，两个开关必须同时检查，客户端 flag 不能充当访问控制。关闭时助手业务路由返回稳定的 `503 assistant_disabled`，不泄露配置。启用前必须显式提供 Chat／Embedding 身份、HTTPS endpoint、价格、北京时间日预算、规范 origin、独立 HMAC secret、runtime 路径和单进程声明，运行 `python -m app.assistant.provisioning` 与 `python -m app.assistant.readiness`，并持有未撤销的 readiness receipt。OpenAPI 路由存在或本地替身通过都不表示真实供应商已可用。

功能开发和人工审计使用仓库根命令 `npm run dev:assistant`，无需在 `.env` 中打开上述生产能力。专用 API 入口只接受 `development`、文件型内容 SQLite、绝对临时 runtime 目录和回环 Web origin；它在环境与本机配置校验通过后才迁移现有内容库，并在开始监听前重建并切换当前已发布 generation、签发仅对本次进程有效的离线 readiness，再启用 gate。Chat 只把命中的已发布证据转换为中文引用摘录，Embedding 使用具备词法相关性的本地 feature hash；二者均为零价格 test provider，不访问真实供应商，并在其他环境 fail closed。

生产进程还必须用 `GAVIN_ASSISTANT_QUALIFICATION_PROFILE_PATH` 选择一份绝对路径的已审阅非秘密 profile，并用 `GAVIN_ASSISTANT_QUALIFICATION_PROFILE_DIGEST` 固定其规范摘要。API 和 Worker 启动校验会把内容库、共同写 fence、媒体、runtime、Qdrant volume，可信代理／origin／heartbeat，Chat／Embedding 模型版本、限制、价格、三预算、pipeline 和 Qdrant 私网地址逐项与该 profile 比较；文件被替换或任一值漂移即 fail closed。真实 provider readiness 还要求显式提供已复核 probe，且其 SHA-256 与 profile path 都必须等于启动时选定值。`.env.example` 列出面向开发与部署操作者的 Settings 配置名，但有意排除只能由测试夹具设置的 `GAVIN_ASSISTANT_TEST_STARTUP_BOOTSTRAP`；示例不提供生产选择，密钥值不得写入 profile、Git、命令行或资格 manifest。

匿名 API 为同源 `POST /api/v1/assistant/sessions`、`GET|DELETE /api/v1/assistant/session` 与 `POST /api/v1/assistant/questions`（SSE）。questions 的畸形 JSON、严格类型、未知字段、问题与 path 边界统一返回 `400 invalid_request`，该 operation 不声明框架默认 422。Session 视图是 additive 消费合同：completed turn 含 question／answer／citations／sources／`body_available`，另有最多一个 `active_turn` 与 `AssistantClientPolicy`；900 秒逻辑保留期到达后即使物理清理重试中也不再序列化正文。公开 SSE 剥离内部 `idempotent`。bootstrap 对已有 session 重签同一 session-bound CSRF 且不刷新 idle TTL；GET／DELETE 只计入 envelope。DELETE 在 origin／metadata／CSRF 失败时不得 tombstone，204 与 202 都撤销两个助手 Cookie；204 只证明本站可读正文与引用已清除，202 只证明清理已发起。

每个付费 runner 捕获 session、epoch、turn、thread 与三条 lease 共用 token。provider 的 `prepared→sending`、stage、terminal、history、hub publish 与 identity-aware Saver adapter 都验证同一 identity；失去 fence 的既有发送最多按价格快照结算 allowlist usage，不能写正文、事件、history、checkpoint 或 live delivery。checkpoint 仅保存当前问题、内部 ID、generation/version/evidence descriptor 等必要非历史正文恢复状态；最近成功历史的问题只在 retrieve 节点局部拼接到 RAG query，历史问答只在 generate 节点临时 hydration，二者都不得成为 LangGraph State 或 node writes。expiry 先读取候选 ID，再逐 session 取得 Saver 共用的 serialization boundary，锁内短事务复检后才 tombstone、安全终结、释放 lease 并关闭 live hub；checkpoint 删除仍由锁外 Saver 自行取得该 boundary。`checkpoint_deleted_at` 只在 awaited Saver 删除和 `checkpoints`/`writes` 零残留复查后成立；失败会保留 null、写 retry fact 并打开 cleanup breaker。会话、幂等、费用账本、SSE journal 和 pinned `AsyncSqliteSaver` 位于独立 `assistant_runtime` SQLite，仅单 API 进程以 owner lock 打开，明确排除于长期备份；SQLite saver 不支持据此推导多 API 进程生产资格。

启用在线问答时还必须分别声明 `GAVIN_ASSISTANT_CHAT_MAX_INPUT_TOKENS`、`GAVIN_ASSISTANT_CHAT_MAX_OUTPUT_TOKENS` 与 operator-declared `GAVIN_ASSISTANT_CHAT_CONTEXT_WINDOW_TOKENS`，并满足 input cap 加 output cap 不超过声明的总窗口。保守 estimator 取完整 UTF-8 byte 上界与可用 provider tokenizer 的较大值，先按完整 pair 从最旧历史裁剪；仍无法同时证明 input cap 和 context reserve 时不发送 Chat 请求。output cap 作为真实 `max_completion_tokens` 下发。三项限制与 estimator version 都绑定 readiness receipt；版本变化后必须在 `checkpoints`/`writes` 零残留时重新签发，旧运行中 checkpoint 不能被新 receipt 接纳。本地配置一致性不证明供应商真实窗口。

问答读取内容库中具备资格的 About 发布修订，不摄入或解析 `apps/web` 源文件；模板静态文字不因此成为个人事实。

## 单管理员问答运营面（默认关闭）

管理 API 提供 `GET /api/v1/admin/assistant`、`PATCH /api/v1/admin/assistant/availability`、有界索引任务列表与 retry、持久 rebuild 创建／查询及显式 finalize。GET 聚合 runtime 与 content 两库各自观察时间，只读本地 allowlist 事实，绝不调用 Chat、Embedding 或 Qdrant live probe；API capability 关闭时也能返回 content 侧 partial snapshot。所有 GET 需要管理员 Session，mutation 另需 CSRF；retry、rebuild、finalize 使用 `Idempotency-Key`，enable 与 finalize 使用精确 version，disable 对 stale version 安全优先。所有响应和错误均 `no-store`。

runtime gate fresh provision 默认 disabled，并把 receipt/config/active generation、cleanup breaker、restore lock 与单调 operational epoch 绑定到 admission、`prepared→sending`、正文写入、Saver 和 publish。停用响应后不会再建立新 session、turn 或 sending；已先越过 sending 的外部调用不能撤回，但旧 epoch 只允许 exactly-once 无正文保守结算。普通 enable 不能清除 `switch_pending`。

Worker 只把隔离 staging generation 标成 `ready_to_switch`，验证使用固定本地非零向量，不新增 Embedding 调用。finalize 由单 API owner 执行 runtime fail-closed marker → content `BEGIN IMMEDIATE` digest/high-water/pointer 切换 → runtime reconciliation；切换后保持 disabled，必须为新 generation 重签 readiness receipt并显式 enable。Chat、query Embedding 与 index Embedding 三账本均按北京时间执行 `settled + reserved + new <= cap`，分开显示且不合并为供应商总账单保证。

历史 Alembic revision 和 `ArticleRevision.source` 已接受的只读旧值属于数据库升级与数据兼容合同，不是当前功能模块。当前路由不再创建这些旧值，但不得仅因现行模块清单中没有对应功能就删除迁移文件或收窄枚举；任何清理都必须通过独立数据迁移 spec 证明现存数据库可升级且历史修订可读。


## 问答管理第二版

`/admin/assistant` 的管理扩展包含 `GET /management`、版本化 `PATCH /budget`、分页 `GET /sync`，以及管理员专用 `/trial/{sessions,session,questions,resume}`。试问每次必须通过管理员登录验证，写请求还校验管理 CSRF；试问 Cookie、HMAC 上下文和 session id 与匿名会话分离。`POST /emergency-stop` 撤销两个执行范围，普通 availability 关闭只撤销访客范围。重新恢复试问不能跳过 readiness、恢复锁、清理保护或切换锁。

升级前停止 API 与 index Worker，执行 `uv run alembic upgrade head` 更新内容库至当前 head（预算表最初由历史迁移 `20260910_0025` 引入），再启动 API 导入当天已有 runtime 费用，随后启动 Worker。当时的预算功能没有新增 runtime schema 迁移；当前 runtime 版本由代码及独立迁移链管理。共同权威是 content 库的预算 policy / reservations 表，历史 index 尝试由迁移导入。默认总上限保守取现有三个分类授权上限的最大值；保留三个原分类上限，管理端不能扩大部署授权。

Runtime 的预留先持久化共同权威，再提交短会话准入；结算在 runtime commit 之后单调投影。失败或缺失记录保持原预留，不自动退还未知费用；旧 runtime 中已结算的尝试不能再次 sending。Worker 的共同预算和 index 分类账本同事务提交，调用前完成预留。每批同步还为一次有界问答留额度；预算不足等待，撤回／删除不依赖付费预留。备份必须包含两个新表，恢复锁同时约束 API 与 Worker 至北京时间次日，预算编辑不能解除恢复锁。

`GET /assistant/availability` 只返回 `available`，no-store，不建会话、不调用模型、不暴露诊断；公开布局在活动页最多 30 秒更新入口。管理 GET 同样只读本地事实。详见 [第二版设计与实施记录](../../harness/docs/product/assistant-management-design.md)。

简历版本与请求保存在内容 SQLite 的 assistant_resume_* 表；PDF 单份上限10MiB、正文200000字符，当前实现成功后只保留一个版本。绑定代次独立于 Profile.version；换址/清空删除旧缓存并撤销资格，失败保留暂停版本供同hash恢复。索引 tombstone 按不可复用版本ID跨代次清理，不会按整个来源误删新版。删除不清除既有备份或承诺WAL安全擦除；下载和解析由既有索引worker执行；当前有效PDF版本由同源只读路由提供。

设置 `GAVIN_ASSISTANT_RESUME_TRUSTED_HOSTS` 为允许的精确域名（逗号分隔，默认空）。首次/换址保存资料原子入队，既有URL由worker首次初始化；同址替换PDF后调用管理员 `POST /api/v1/admin/profile/resume/refresh`（Session、CSRF、binding_epoch）。`GET /api/v1/admin/profile/resume`只读返回同步状态，不触发下载；202表示排队，409表示绑定冲突/未配置，429携带60秒手动冷却剩余时间。请求合并，失败暂停，网络暂时故障最多追加1/5/15分钟三次重试并尊重Retry-After；无定时检查或年龄过期。复用既有索引worker并优先处理到期简历请求，外部下载/解析不持内容写事务或备份锁；90秒lease到期可接管，崩溃同样消耗最多四次的尝试预算。

`GET /api/v1/assistant/resume/{version_id}`只返回当前绑定且已索引的PDF原字节，使用固定附件文件名、no-store和nosniff；失败暂停、换址/清空及无效版本返回404，不建问答会话或触发外部请求。最后成功索引时间保留为历史记录，不代表当前可用。提示将简历/关于页视为自述，冲突需引用双方；不可用说明只允许后端确认的固定无引用操作提示，不能成为任意无来源断言。生成前和最终发布前仍复核证据，checkpoint仅含描述符。

来源联调在隔离SQLite经管理员发布关于页/配置简历、真实PDF解析与worker索引、真实问答图验证双来源引用及文章回归；同址替换、下载失败部分回答和撤销也在同一流程检查。下载与模型为确定性夹具，浏览器附件走真实Web代理/API；该结果不证明真实模型质量、目标PDF服务缓存行为或生产资源资格。真实公开简历另外通过无DNS/下载替身的标准子进程、隔离导入/检索、附件字节、同址刷新复用和清空撤销检查，见[实际文件记录](../../plan-build/assistant-upgrade/completed/assistant-upgrade-verification/Q4-03.md)。上述记录确认该次本机问答库导入和 E5/Qdrant 索引；快捷启动器管理 Worker。当前是否运行/同步需读取实际状态，历史记录未验证外部文件替换后的缓存行为。

中文紧邻数值与单位参与支持材料核对；完整逗号句保留限定，作者自述仅在本人来源中允许归属明确的转述。已知无据个人经历、共现推依赖被拒绝；完整解释风险的教程引文允许讨论，但不豁免实际凭据或引文外执行请求。有限规则不保证通用语义正确，详见[缺口修复边界](../../harness/docs/decisions/20260911-assistant-gap-closure.md)。

支持材料一致的比较符号、数组下标和简单泛型可通过输出结构校验；HTML、图片、危险链接及游离引用标记仍拒绝。数组表达在生成的 answer 字符串中用行内反引号标界，真实引用在边界外由服务端添加，避免 a[1] 与来源编号混淆；公开、管理及恢复读取相同结果。此标界不授权执行 Markdown/HTML，也不放宽事实或数值校验。

输入和证据规则现在按完整、有限的中英文讨论框架处理邮件、数据库和命令相关动作词；仅讨论对应功能/流程/风险不等于要求执行。框架外的请求仍扫描，角色覆盖与泄露检查不被讨论豁免。精确的 YOUR_API_KEY、YOUR_SECRET_KEY、YOUR_PASSWORD 赋值示例（含配对引号）可用，附加尾缀、混合真实凭据和 URL 凭据不豁免；检索及恢复继续检查标题、heading 和正文。离线发布/索引/hydrate 测试仅证明这些规则行为，尚不能证明实际模型在用户、资料或历史注入下的抗攻击效果。

2026-09-12 用户确认本机调用名可切换为 `deepseek-flash`。本机合同同时保留 `deepseek-v4-flash` 兼容，拒绝其他未经核对的名字；新名字须重新绑定同一费用账本的授权，旧次数/费用/失败仍累计。`deepseek-flash` 的版本关系目前仅属操作者声明，不能因名字切换伪造供应商版本证明、旧 probe/readiness 兼容或生产资格。实际模型响应名仍须精确匹配请求配置。

Q2-06 正常回答修复对文章自身的“本/该教程”、精确当前标题引介、解释了/解释及调用服务的有限连接词做等价核对；支持一个完整邮件通知关系的有限英文转述，不把关键词共现当作翻译支持。否定、条件、主体、数值及句后撤回仍参与完整核对。提示明确解释动作与执行动作的区别，优先简洁完整原文事实。空 blocks 仍被拒绝；离线重放和提示预算通过不能证明真实模型空答已经消失。自由翻译、任意资料缺失说明仍可能误拒，真实质量在追加次数授权后的 G07 复验中单独记录。

教程对同一引号主题明确说明“为何危险”并紧邻“它……”原因时，允许合并为“之所以危险，是因为它……”等有限完整关系。主题和完整原因分别一致才通过，不从普通共现创造因果，否定、条件、其他主体和撤回不丢弃。提示明确答案语言与原文支持quote语言不同不构成证据缺失；这仍需真实模型复验，不保证任意跨语言表达都能通过确定性核对。G07运行器可精确选择样例诊断，调用继续累计于原签名账本。

当前问题在提示的历史与证据之后呈现，强调按问题语言回答相关内容、支持引文保留原文语言。问题仍是不可信数据，不获得修改系统规则的权限。完整邮件通知关系可接受有限的英语主动/被动表达；协议、否定、限定和主体必须仍与原文一致。提示顺序调整本身不证明模型相关性或语言遵循性。

对不含中文且以how/what/why等明确英语疑问词开头的问题，系统额外选择固定English回答约束；不把用户原文拼入系统消息，不把任意拉丁字母语言当英语，其他情况维持按问题语言回答。教程“介绍某功能的方式是：调用……”与原文完整同关系核对，不能丢弃条件或改变调用对象。语言约束仍是提示，实际遵循性另验。

“文章介绍某功能：教程介绍同一功能，……”只有在前后主题完全一致时才能去除重复引介，保留后句完整事实；不同主题不得消除。邮件通知英文关系仍是有限语法，未覆盖的新转述不能自动视作有据。校验器单独变更时，可在确认生成提示完全相同后重放已留存真实模型输出；这不会把旧失败篡改成当时通过，也不代表模型新一轮生成已验证。


在线检索的历史查询、同步 query Embedding、Qdrant/SQL hydration 由每个 AssistantOnline 自有的有界线程池执行；容量复用 `assistant_embedding_provider_max_concurrency`（缺省为 1），提交前等待槽位，线程内创建和关闭内容 session，只返回 descriptor。排队取消不会提交工作；已开始的同步 IO 不可强制中止，取消消费者后仍占槽直到实际结束，保持原供应商超时、预算预留与身份围栏。停机先取消图并处理终态，再等待检索工作完成，最后关闭 saver、控制数据库和 owner lock，因此慢或不遵守超时的客户端会延长停机。该边界覆盖 retrieve 节点；其他节点的短同步数据库访问和生产 P95 尚不在此项验证范围。合成慢调用测试检查其他会话、心跳及 sweep 能在检索结束前响应，不能替代目标部署的负载测试。


预算诊断使用 `assistant/prompt_budget.py` 的纯数值输出；UTF-8 字节各项可加总，分别分词的 component tokens 不可直接相加。候选与最终证据、历史裁剪、正文/supports/JSON 开销分开记录；空 blocks 和非法 JSON 不算非空有效输出。离线入口 `plan-build/assistant-gap-closure/evaluation/audit_prompt_budget.py` 只读取 SHA 固定的官方 tokenizer 数据和 G07 已保留响应，拒绝提示构造漂移，不调用模型。

2026-09-12 的 24 个有限合成样例中，保守估算 7297–7493，供应商输入 usage 1305–1351，前者约为后者 5.44–5.60 倍；官方文本消息模板计数每例少 25 tokens，输出计数 24/24 与实际 usage 一致，输出最多 172/512 且 finish=stop。此结果不证明未知响应版本或服务端模板匹配，也不证明长回答不会截断，因此保持现有保守准入。四个中英文 SMTP 可答输入样例（无简历状态提示/明确不可用）最低估算分别 7193/7606、7344/7757，少一个输入单位或 context 少一个输出预留单位即拒绝；这是带固定来源的样例阈值，不是任何问题通用的最低值。8000 输入/512 输出及 3/9 元每百万 tokens 的本机配置下，两次 Chat 最坏预留仍为 57216 micro-CNY（0.057216 元），不靠提高上限解决余量不足。

### 无结果调用与阶段三验证边界

供应商既未返回原始响应也未返回解析结果时，沿用 `provider_result_unknown` 终态：调用保守按最大预留结算为 unknown，不发起格式纠正重试。已收到但格式错误的响应仍受原两次上限和输入预算约束。阶段三并发、心跳、取消、迟到结果和费用回归使用本地替身；不代表真实供应商质量、持续负载或生产延迟已验证。

有限多轮：只从上一条仍在TTL内的成功回答中取唯一公开来源位置，复核当前发布投影再检索；来源名称只帮助确定对象，旧问题/答案正文不进入新提示。对象缺失、多来源、条目序号或失效时返回 `clarification_required`；界面显示“需要明确对象”，刷新可恢复，明确对象后可继续。独立问题不拼接旧问题。最多四轮及原TTL保留；任意自然语言指代和答案条目映射仍未支持，实际多轮质量待Q5。

页面优先只在问题明确指向当前页（例如“这篇文章”“this page”）或成功解析唯一来源时启用。可识别的全站完整清单/总数和全局最新/当前任职请求分别返回 `completeness_unverified` 与 `freshness_unverified`，在模型前停止；界面明确“完整性尚未核验”或“时效尚未核验”。普通局部清单、教程技术计数和限定的历史事实仍走证据问答。规则覆盖有限，未建立全量库存、事实时效证明、通用重排或任意长文完整性，片段不得冒充全文。

阶段四收尾回归涵盖跨来源冲突/自述、About旧版本失效、简历发送/生成/发布撤销复检、版本化PDF下载及危险路径拒绝；历史正文既不补充新事实也不进入checkpoint。此离线范围仍不证明当前独立内容质量、实际模型成功率或生产资格。
