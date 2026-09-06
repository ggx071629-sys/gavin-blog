---
id: operations-local-real-qa
level: L2
summary: 本机真实 E5 与 DeepSeek 问答的启动、维护、验收及资源估算
load_when:
  - local-real-qa
author: Gavin
---

# 本机真实问答交接

适用日期：2026-09-06。仅本机 development；没有生产资格，也未验证 2 核 / 4 GB 虚拟机。

## 配置与启动

1. API `.env` 保持 `GAVIN_ENVIRONMENT=development`、在线开关关闭，填写真实 Chat Key 和相互独立、至少 32 字符的 session、CSRF、IP、readiness、proxy HMAC 密钥。密钥必须持久保存，不在每次启动时重新生成。模型、版本、token 上限和价格例子见 [配置模板](../../../apps/api/.env.example)。已获准本轮测试总额 1 元、Chat 北京时间每日 2 元；本次最多提交 14 个问答请求，每次最多两次模型调用。
2. `.env.e5` 使用已固定的 E5 FP32 模型、384 tokens 切片/64 overlap、batch=1/concurrency=1，设置本地 Embedding 价格与查询/索引预算为 0；配置文件型内容 SQLite、8091 Embedding 与 8092 Qdrant。模型与 Qdrant 分别使用自己的本地鉴权密钥，不能收到 Chat Key。
3. 按 [API E5 说明](../../../apps/api/README.md) 启动模型和 Qdrant，保留原存储目录。模型入口为 `embedding_service/.venv/Scripts/python.exe scripts/run_e5_service.py`；仅向该进程提供 `GAVIN_E5_MODEL_DIR`、`GAVIN_E5_API_KEY` 及离线 Hugging Face 设置。Qdrant 使用既有 v1.18.3 binary、`QDRANT__SERVICE__HOST=127.0.0.1`、HTTP 8092/GRPC 8093、既有 storage path，并关闭 telemetry。不要启动第二份模型，也不要将存储目录改成临时空目录。
4. 在 `apps/api/` 使用原 CLI：`.venv/Scripts/python.exe scripts/run_assistant_provider_qualification.py --local-chat --ledger data/assistant-qualification/local-chat-ledger.json --output data/assistant-qualification/local-chat-probe.json --approve-max-micro-cny 1000000 --max-calls 3`。它会复用已有 ledger，失败/未知请求不会自动重复，原始响应和密钥不进入证据。已有新鲜成功 probe 时跳过此付费步骤。
5. 根目录执行 `npm run dev:assistant:real`，等待 ready。启动器先验证本机签名 probe、E5 健康和 active generation，再签发或复用 readiness 并打开运营 gate。Web 入口、API 能力和运营 gate 三者此时都打开；仅监听回环地址。网络沙箱必须允许 Chat 的 HTTPS 出站，服务可启动不等于 Chat 网络可达。

## 启停、更新与恢复

- 停止：先 Ctrl+C 退出问答启动器，它负责停止本轮 Web/API 子进程；再停止专用模型、Qdrant 和 Worker 终端。runtime、索引、模型和费用文件保留。`npm run dev:assistant` 是独立离线入口，不能用它的成功替代真实验收。
- 索引更新：停止真实问答以释放 runtime 锁，保留 `.env.e5` 的同一内容库；在 `apps/api/` 运行 `.venv/Scripts/python.exe -m app.local_embedding.local --env-file .env.e5 rebuild`，记录返回 generation，再用同一入口 `finalize <generation>`。如旧会话尚有 checkpoint，先按原清理流程清除；不能删 runtime 绕过残留检查。重新启动后按新 generation 校验 readiness。持续消费 outbox 的独立 Worker 使用同一 `.env.e5` 配置，不能误用 `.env` 默认库。
- Key、模型、价格、token 或预算调整：先关闭 gate/停止 API，保留旧 probe/ledger/费用；配置变更使旧签名失效。当前本机合同绑定已批准的每日 2 元；其他额度需先更新批准范围及配置合同，再在新的明确有界测试范围内探测。旧 ledger 的配置漂移会拒绝执行，不可删除或覆盖旧 ledger 来获得新额度。24 小时后需要新鲜 probe 才能重新启动。
- 日常费用以 `assistant_chat_budgets` 的 settled+reserved 为准；未知结果按上限计费并打开熔断。调查供应商与网络后才能恢复，不能清零费用、改日期或复制空库。本轮网络沙箱故障保留 28,608 micro-CNY 的最高费用；只在确认非计费连通性恢复、reserved=0 后解除了本机熔断，失败事实未删除。
- v4 租约迁移：启动器在持有 runtime 独占锁时执行。旧版本同一个 scope/key 的唯一约束错误地限制了全局并发；新约束包含 owner turn。回滚需关闭入口、停止/排空租约，再执行原 Alembic 降级流程；有租约时降级拒绝，不自动丢弃它们。降级后需由对应版本的 provisioning/readiness 重新验证，禁止仅替换旧代码继续启用。
- 日志：启动器向当前终端输出；本轮原始采样、合成问答结果和网络恢复记录仅留在 `apps/api/data/qa-real-20260906/`，不提交。控制库保留预算与必要脱敏审计；DELETE 会清除会话正文/checkpoint 并保留预算事实。生产备份仍排除 runtime。

## 验收与资源口径

实测与最终费用见 [阶段 F manifest](../../verification/evidence/20260906-local-real-qa.benchmark.json)。功能实测使用已有 3 篇公开文章与真实 E5/Qdrant/DeepSeek：中文、英文到中文证据、连续追问、多段引用、证据不足与两路并发。引用结果逐项对照公开原文。模型响应只报告 alias，固定版本来自官方文档和配置声明，不能声称响应证明了具体版本。

自动化故障回归使用真实应用图与可控传输夹具，覆盖 Embedding/Qdrant timeout 后 FTS 降级、Chat 异常/截断/非法 JSON、预算耗尽、租约容量、DELETE/晚到结果和清理。它们是故障注入证据，不能当作供应商真实发生 429/500 的证据。

阶段 F 复用阶段 D 的进程采样器，补测真实 Chat 的 API 工作集、私有内存、CPU 核当量和 HTTP/SSE 端到端耗时。此次 Web 是开发服务器、语料仅 3 篇、没有独立 Worker，因此不将四角色合计冒充部署实测。完整容量继续以 [阶段 D 五角色结果](e5-retrieval-evaluation.md#2026-09-06-最终容量报告) 为基线，再加入本次 API 增量保守上界；具体计算、样本数与限制记录在 manifest。短时双并发不证明长时稳定，也不证明云端 vCPU 性能。

真实并发暴露了 saver 的隐式写事务跨 await 阻塞同步控制连接。运行时 aiosqlite 使用 autocommit，使每条语句原子提交；原 saver 表、序列化格式、thread identity、每会话 DELETE 屏障和删除后零残留复查继续保留。多语句中断可能留下部分 checkpoint/writes，由原恢复/清理机制处理，不能由“部分写入”推导可交付答案。修复后补两次有界请求，问答总提交上限由内部计划的 12 次增至 14 次，费用批准仍为 1 元。

生产部署另立任务：资格 profile、最终 HTTPS edge、可信 IP 链、SSE 缓冲、readiness 与真实目标机器验收均未完成。本机入口不会放宽这些要求。

最终补测：71 个样本，API 工作集峰值约 531 MiB、私有分配峰值约 994 MiB，API 短时峰值约 0.52 个本机逻辑核。相对阶段 D 的 API 内存增量保守界约 59 MiB，完整规划仍为 **7–8 GiB 内存、约 12 GiB 应用磁盘**；将本次 API CPU 峰值保守叠加阶段 D 忙碌窗口，建议初始按 **3 个同档逻辑核**留量（可能重复计入 API，不是三核实测）。最终双并发耗时 1.546/3.738 秒，一题回答、一题证据不足；DeepSeek/Codex 配置题的正向覆盖尚未证明，保留为质量限制。总保守费用 **0.094950 元**，其中 0.028608 元是网络未知请求的最高计费；实际供应商账单可能更低。
