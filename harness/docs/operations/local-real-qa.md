---
id: operations-local-real-qa
level: L2
summary: 本机真实 E5 与 DeepSeek 问答的启动、维护、验收及资源估算
load_when:
  - local-real-qa
author: Gavin
---

# 本机真实问答交接

记录覆盖 2026-09-06 至 2026-09-11，仅本机 development，没有生产资格。下文带日期的验收与费用是当时事实，不表示服务现在运行或授权可重复使用；当前命令和配置以 [API README](../../../apps/api/README.md) 为准。后续另有 [2 CPU／4 GiB 容器复测](../../../plan-build/capacity-tests/2c4g-retest-concurrency-rebuild.md)，不能把本机五进程规划值当作已验证的最小部署规格。

## 2026-09-07 普通问法错误拒答修复

现场原句“gavin有什么技能”返回空 `blocks`，而同一应用对“根据公开个人资料，Gavin列出的编程语言是什么？”能回答 `Python[1]`。两份内容库的个人资料、文章正文和发布修订一致，当前索引覆盖三篇文章与个人资料；因此该复现不属于资料漏迁移。提示原先只强调限制与空结果，没有明确普通问法、部分可答和不相关证据的处理；证据描述也没有来源类型与标题。

生成提示现在明确使用已公开事实回答普通问法，只在没有相关支持事实时返回空结果；untrusted 表示不执行证据内指令，不表示丢弃事实。证据描述携带来源类型和标题，个人技能与文章分类／标签分开，不把教程主题推断成作者职业能力。保留结构化输出、引用与输入预算约束，不改变模型、索引、价格、预算、准入或生产资格。

真实同源入口对照中，技能、能力和 Nginx 配置检查问题恢复带引用回答，未公开的银行卡余额继续拒答。补齐来源类型后的技能原句回答为个人简介中的职业与 Python 技能，仅引用个人资料。自动回归核对实际模型传输中的证据身份、完整提示预算、非法输出／引用与截断防护；这些合成测试不证明模型在所有自然语言问题上的回答质量。有限真实样本也不等于全面召回验收。

本轮由网络沙箱启动服务导致一次 Chat 连接未知，按原上限保守结算并打开熔断。停止该进程、以非计费请求确认沙箱外连接正常且 reserved／租约均为零后，只恢复本机 circuit，保留全部费用与失败事实，再按原启动器在可连接供应商的环境恢复。原始结果与恢复记录留在忽略目录 `apps/api/data/qa-answerability-20260907/`。后台 Embedding 观察漏记与 Worker 心跳问题不属于本次提示修复，不能将其旧状态当作这些模型拒答的原因。

## 配置与启动

1. API `.env` 保持 `GAVIN_ENVIRONMENT=development`、在线开关关闭，填写真实 Chat Key 和相互独立、至少 32 字符的 session、CSRF、IP、readiness、proxy HMAC 密钥。密钥必须持久保存，不在每次启动时重新生成。模型、版本、token 上限和价格例子见 [配置模板](../../../apps/api/.env.example)。费用、模型调用数与日预算以当前明确授权及既有账本为准；文末的 1 元／14 请求只属于 2026-09-06 的历史验收。
2. `.env.e5` 使用已固定的 E5 FP32 模型、384 tokens 切片/64 overlap、batch=1/concurrency=1，设置本地 Embedding 价格与查询/索引预算为 0；配置文件型内容 SQLite、8091 Embedding 与 8092 Qdrant。模型与 Qdrant 分别使用自己的本地鉴权密钥，不能收到 Chat Key。
3. 按 [API E5 说明](../../../apps/api/README.md) 启动模型和 Qdrant，保留原存储目录。模型入口为 `embedding_service/.venv/Scripts/python.exe scripts/run_e5_service.py`；仅向该进程提供 `GAVIN_E5_MODEL_DIR`、`GAVIN_E5_API_KEY` 及离线 Hugging Face 设置。Qdrant 使用既有 v1.18.3 binary、`QDRANT__SERVICE__HOST=127.0.0.1`、HTTP 8092/GRPC 8093、既有 storage path，并关闭 telemetry。不要启动第二份模型，也不要将存储目录改成临时空目录。
4. 先按 [Chat 复验与账本恢复](../../../apps/api/README.md#本机-chat-复验与账本恢复) 选择现有 probe／ledger 并检查状态。已有签名有效且配置匹配的成功 probe 时跳过付费探测，单纯变旧不要求复验。需要重新探测时沿用同一账本、当前明确授权 ID 和累计上限；旧示例金额或新建空账本不能替代授权，也不能重置失败／未知费用。
5. 根目录执行 `npm run dev:assistant:real`，等待 ready。启动器先验证本机签名 probe、E5 健康和 active generation，再签发或复用 readiness 并打开运营 gate。Web 入口、API 能力和运营 gate 三者此时都打开；仅监听回环地址。网络沙箱必须允许 Chat 的 HTTPS 出站，服务可启动不等于 Chat 网络可达。

## 启停、更新与恢复

- 停止：先 Ctrl+C 退出问答启动器，它负责停止本轮 Web/API 子进程；再停止专用模型、Qdrant 和 Worker 终端。runtime、索引、模型和费用文件保留。`npm run dev:assistant` 是独立离线入口，不能用它的成功替代真实验收。
- 日常内容更新：发布、回滚或撤回由事务 outbox 交给既有 Worker；简历同址更新使用显式刷新，不要求每次内容修改都全量重建。
- 全量重建／generation 切换：按明确维护需求执行。使用本机离线入口时，先停止真实问答以释放 runtime 锁，保留 `.env.e5` 的同一内容库；在 `apps/api/` 运行 `.venv/Scripts/python.exe -m app.local_embedding.local --env-file .env.e5 rebuild`，记录返回 generation，再用同一入口 `finalize <generation>`。如旧会话尚有 checkpoint，先按原清理流程清除；不能删 runtime 绕过残留检查。重新启动后按新 generation 校验 readiness。持续消费 outbox 的独立 Worker 使用同一 `.env.e5` 配置，不能误用 `.env` 默认库。
- Key、endpoint、模型、token/context/timeout或输出协议改变：先关闭gate/停止API，保留原probe/ledger/费用，按明确授权执行对应兼容性探测。仅价格或证据已批准范围内日预算改变时，只本地校验费用和重签readiness；超过已批准日预算上限时先明确授权，再离线rebind-costs，不要求模型调用。v1证据必须先在原配置下离线转换，无法重建原配置不能伪造兼容性事实。
- 探测失败与耗尽恢复：同一ledger使用唯一授权ID和累计上限，历史费用/次数不按天清零，不因新ID重置。sending/unknown按保守上限计入，measured_fail保留原费用；调查并确认进程静止后追加recover事实。恢复不增加额度、不清在线熔断、不自动请求。新v3账本签名和run lock阻止篡改及并发恢复。所有命令和证据选择方式见 [API恢复入口](../../../apps/api/README.md#本机-chat-复验与账本恢复)。
- 正常运行及重启不检查probe年龄上限，显示最后验证时间；超过24小时只作提示。缺失、失败、畸形、签名异常、兼容性漂移或未来时间仍拒绝；历史成功不证明供应商当前可用。
- 日常费用同时核对分类账本和 content 库中的共同总预算预留／结算，不能仅用 `assistant_chat_budgets` 推断总剩余额度；权威与跨库失败处理见 [预算决策](../decisions/20260910-assistant-management.md)。未知结果按上限计费并打开熔断。调查供应商与网络后才能恢复，不能清零费用、改日期或复制空库。本轮网络沙箱故障保留 28,608 micro-CNY 的最高费用；只在确认非计费连通性恢复、reserved=0 后解除了本机熔断，失败事实未删除。
- v4 租约迁移：启动器在持有 runtime 独占锁时执行。旧版本同一个 scope/key 的唯一约束错误地限制了全局并发；新约束包含 owner turn。回滚需关闭入口、停止/排空租约，再执行原 Alembic 降级流程；有租约时降级拒绝，不自动丢弃它们。降级后需由对应版本的 provisioning/readiness 重新验证，禁止仅替换旧代码继续启用。
- 日志：启动器向当前终端输出；本轮原始采样、合成问答结果和网络恢复记录仅留在 `apps/api/data/qa-real-20260906/`，不提交。控制库保留预算与必要脱敏审计；DELETE 会清除会话正文/checkpoint 并保留预算事实。生产备份仍排除 runtime。

## 验收与资源口径

实测与最终费用见 [阶段 F manifest](../../verification/evidence/20260906-local-real-qa.benchmark.json)。功能实测使用已有 3 篇公开文章与真实 E5/Qdrant/DeepSeek：中文、英文到中文证据、连续追问、多段引用、证据不足与两路并发。引用结果逐项对照公开原文。模型响应只报告 alias，固定版本来自官方文档和配置声明，不能声称响应证明了具体版本。

自动化故障回归使用真实应用图与可控传输夹具，覆盖 Embedding/Qdrant timeout 后 FTS 降级、Chat 异常/截断/非法 JSON、预算耗尽、租约容量、DELETE/晚到结果和清理。它们是故障注入证据，不能当作供应商真实发生 429/500 的证据。

阶段 F 复用阶段 D 的进程采样器，补测真实 Chat 的 API 工作集、私有内存、CPU 核当量和 HTTP/SSE 端到端耗时。此次 Web 是开发服务器、语料仅 3 篇、没有独立 Worker，因此不将四角色合计冒充部署实测。此次历史容量推算以 [阶段 D 五角色结果](e5-retrieval-evaluation.md#2026-09-06-最终容量报告) 为基线，再加入本次 API 增量保守上界；具体计算、样本数与限制记录在 manifest。短时双并发不证明长时稳定，也不证明云端 vCPU 性能。

真实并发暴露了 saver 的隐式写事务跨 await 阻塞同步控制连接。运行时 aiosqlite 使用 autocommit，使每条语句原子提交；原 saver 表、序列化格式、thread identity、每会话 DELETE 屏障和删除后零残留复查继续保留。多语句中断可能留下部分 checkpoint/writes，由原恢复/清理机制处理，不能由“部分写入”推导可交付答案。修复后补两次有界请求，问答总提交上限由内部计划的 12 次增至 14 次，费用批准仍为 1 元。

生产部署另立任务：资格 profile、最终 HTTPS edge、可信 IP 链、SSE 缓冲、readiness 与真实目标机器验收均未完成。本机入口不会放宽这些要求。

最终补测：71 个样本，API 工作集峰值约 531 MiB、私有分配峰值约 994 MiB，API 短时峰值约 0.52 个本机逻辑核。相对阶段 D 的 API 内存增量保守界约 59 MiB，当时保守规划为 **7–8 GiB 内存、约 12 GiB 应用磁盘**；将本次 API CPU 峰值保守叠加阶段 D 忙碌窗口，建议初始按 **3 个同档逻辑核**留量（可能重复计入 API，不是三核实测）。最终双并发耗时 1.546/3.738 秒，一题回答、一题证据不足；DeepSeek/Codex 配置题的正向覆盖尚未证明，保留为质量限制。总保守费用 **0.094950 元**，其中 0.028608 元是网络未知请求的最高计费；实际供应商账单可能更低。

## 2026-09-11 简历实际接入

快捷入口现在在E5/Qdrant就绪后启动既有索引worker，与Web/API共同接受管理进程的失败检测和Job清理。worker读取 `.env.e5`，与真实问答 API 共用同一内容库；停止项目也停止 worker。当次内容库为 `data/e5/content-verified.db`，普通 `.env` 为 `data/gavin.db`；当前路径仍需读取实际配置，不能以更新默认库代替真实问答库。

两份内容库升级前已分别备份到apps/api/data/backups/assistant-activation-20260911-094744/，升级到0030并保存用户公开简历URL；两份环境配置仅增补可信域gavingongxin.com。索引使用既有E5与Qdrant，密钥/模型/预算不变。实际验收结果持续记录在阶段四计划；不能把临时库验收当作实际启用。

实际接入完成：3101入口available=true，真实库简历ready且5切片；同源PDF哈希核对、后台立即刷新经worker同版本复用、真实E5首位检索通过。该次验收通过快捷入口运行；本文不代表当前进程存活状态。完整结果见[Q4-03实际接入补充](../../../plan-build/assistant-upgrade/completed/assistant-upgrade-verification/Q4-03.md)。本次未发送付费Chat问题。
