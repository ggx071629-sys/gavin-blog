# 问答助手来源接入契约

2026-09-11；现行来源契约；代码已接入，阶段验收与真实文件结果见执行计划。依据：[共识](ASSISTANT-UPGRADE-DESIGN.md)、[最终参数](completed/assistant-upgrade-design/Q1-02.md)。小时级检查方案已撤回；以下没有周期检查或时间过期。

## 来源与资格

- `about:1`：只投影 `AboutPage.current_revision_id` 指向的已发布修订，版本使用不可变 revision ID，标题“关于 Gavin”，路径 `/about`。正文按结构提取 statement、capabilities 的标题/说明/tags、now 的文字状态、editorial_topics、site.description 和 stack；不把技术栈自动解释为个人熟练程度，不提取装饰标识或草稿。
- 增加明确的关于页修订资格标记：自动 seed 为 false，管理员 publish/rollback 生成的新修订为 true。既有 revision_number > 1 或 source=rollback 可按现有只追加发布流程回填 true；旧 revision 1 无明确主动发布证据则 false。迁移不修改历史迁移文件，不改变公开关于页展示。回滚到默认文案仍是一次主动操作，生成的新修订可用。
- 发布/回滚在同一内容事务更新指针并登记 about outbox；只保存草稿不触发。新版本指针提交即使旧证据不合格，索引未完成时该来源不可用；既有其他来源继续回答。
- `resume:1`：绑定单例 Profile 的独立简历绑定代次 `binding_epoch`，不使用整个 Profile.version 作为简历身份；只改姓名等不会重复下载。URL 换址/清空立即增加 epoch 并撤销旧来源。
- 简历版本使用随机不可复用 version ID，并保存 binding_epoch、原始文件 SHA-256、提取管线版本。相同绑定且 hash/管线版本相同复用解析和索引；A→B→A 换址不能复活原 A 的引用。
- 合格简历要求当前绑定、当前成功版本、未失败/撤销、索引版本一致；没有年龄限制。检索、hydrate、生成前和最终发布复检均使用同一判定。已开始发送后不能撤回访客已收到的文本。

## 持久化与清理

- 内容 SQLite 所有：新增单例 resume source 状态、不可变 resume version、刷新任务记录。保存配置绑定代次、请求序号/lease/fence、阶段、当前版本、最后尝试/成功检查时间、最后成功索引时间、脱敏错误码和重试时间；API 与 worker 共用内容库事务。
- PDF 原始字节（每份最多 10 MiB）与按页提取正文保存在内容 SQLite 版本记录，避免新增部署目录和跨文件原子提交。最多保留一个成功/暂停版本及一个候选；旧版不形成长期履历档案。增加数据库体积属于该方案成本。
- 下载和解析在事务外进行；提交前在短事务复核 epoch、request ID、worker owner fence 和 lease。失配结果直接丢弃，不写版本/outbox，不将正文写入错误日志。
- 同址手动检查期间可继续使用既有成功版本；检查报错立即暂停。下载发现新 hash 后先撤销旧资格，再解析并提交候选，索引就绪才启用；新旧片段不混用。成功确认同 hash 可恢复暂停版本，不重复解析。
- 换址/清空事务立刻撤销快照访问、删除旧 PDF/正文缓存并登记版本限定 purge；索引向量清理异步可重试，但资格检查立即拒绝旧片段。替换成功清理被替换版本；失败保留最多一个暂停版本供同 hash 恢复，不能对外使用。
- 所有内容数据和 PDF 版本随现有内容 SQLite 备份；Qdrant 向量可重建。问答 runtime/checkpoint 不保存 PDF/正文、不进入长期备份。恢复后仍遵循原运行 gate 与资格流程；不能只恢复向量作为事实库。
- 删除表示应用访问撤销和数据库行清理，不承诺已下载文件、既有备份或 SQLite/WAL 物理字节被安全擦除；沿用已有备份保留策略，不擅自删除备份。

## 调度与状态

- Profile URL 首次配置、换址和管理员显式刷新登记有界任务；既有索引 worker 处理，无额外常驻服务、无定时重新检查、访客请求不触发下载。
- 状态为 `unconfigured`、`pending`、`checking`、`parsing`、`indexing`、`ready`、`failed`；另以 `usable` 表示来源资格，允许 checking 时旧版仍可用。错误详情只暴露固定码和可操作说明，不能回传 PDF、URL 查询秘密或第三方响应原文。
- 单次请求最多三次暂时失败重试，沿用 Q1-02 退避；任务重启恢复不新增无限重试，不因重建或长 outbox 队列永久饥饿；被替换的请求不能迟到提交。
- 无可信域配置时保存 URL 成功但同步失败码 `blocked_host`；其他固定码包括 download_timeout、download_failed、too_large、not_pdf、too_many_pages、encrypted_pdf、text_unavailable、parse_failed、parser_unavailable、index_failed。配置修复后通过“立即刷新”重试。
- 手动刷新成功接收只表示排队，不表示已同步；后台展示最后成功检查与索引阶段，成功检查时间不冒充索引完成时间。

## HTTP 与引用

- 保留 `PATCH /api/v1/admin/profile` 的乐观锁、Session 和 CSRF；URL 变化和任务入队原子提交。GET 不能产生外部下载。
- `GET /api/v1/admin/profile/resume`：管理员只读，返回上述同步状态、usable、binding_epoch、当前 request/version ID、时间及错误，不返回全文或 PDF 字节，响应 no-store。
- `POST /api/v1/admin/profile/resume/refresh`：Session+CSRF，请求包含期望 binding_epoch；过期绑定 409、未配置 409、冷却 429 并带 Retry-After；同绑定正在处理则合并返回 202 与当前 request ID。首次/换址自动请求不依赖前端再调用刷新。
- `GET /api/v1/assistant/resume/{version_id}`：同源公开 PDF 字节路由，只服务当前有效版本，不重定向外部 URL，不接受任意 URL；不可用/撤销返回 404。Content-Type application/pdf、Content-Disposition attachment（安全固定文件名）、Cache-Control no-store、nosniff；只读请求不建会话、不触发下载或模型调用。
- 引用仍由后端把 evidence alias 解析为固定路径；模型不能生成 href。前端引用白名单只增加 `/about` 与严格匹配的简历版本路由；继续拒绝任意外链、编码路径和查询参数。PDF 引用使用普通链接而非 Nuxt 页面导航；“查看简历”仍打开 Profile 配置的原 URL。
- 引用显示“Gavin 简历”，页码放 heading_path；来源类型扩展 constants、数据库 CheckConstraint、管理 schema、OpenAPI/派生类型和 Web 消费类型。现有 citation/source JSON 形状可保留，不凭空增加不需要的公开 source_type 字段。
- 老会话中的旧引用允许显示，但点击被撤销版本返回不可用，不能静默跳到新版；成功回答与 PDF 版本一致性优先于永久可点击性。

## 回答边界

沿用既有证据片段、费用和历史预算，只将检索相关片段送模型；about/resume 明确自述可支撑个人事实，不推断熟练程度或经历。同一事实冲突时明确列出两方说法并引用，不自行排序。简历不可用且问题涉及其缺失信息时说明“简历当前不可用”，有其他有效证据则回答支持部分；不把来源状态冒充事实引用。

## Q1-04 交接

关于页、简历分别建立实施 spec；将新解析子进程、网络与资源边界纳入简历 spec。Q1-02 对资源限制是要求，不是已验证承诺，无法强制执行的平台必须失败关闭。产品验收覆盖迁移、事务失效、混合检索、真实 UI 引用及刷新；真实文件与付费供应商结果单独记录，不能用夹具声称生产就绪。
