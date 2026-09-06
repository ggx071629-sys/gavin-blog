---
id: spec-20260906-local-e5-retrieval
level: L1
summary: 在 Windows 开发机接入固定 E5 CPU 服务和双语检索，保持生产关闭
load_when:
  - task:20260906-local-e5-retrieval
task_id: 20260906-local-e5-retrieval
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260906-local-e5-retrieval.md
documentation_reason: 新增独立模型进程、固定制品、token 切片及真实本地检索操作，需明确身份、资源和运维边界。
state_history:
---

# Context

按根 build-qa.md 执行 A–C 和 D 的本机部分。管理员确认服务器尚未准备好，先完成本机。开发机 Windows AMD64、16 逻辑 CPU、D 盘可用约 282 GB；内存和模型网络待实测。模型目录 apps/api/data/models/multilingual-e5-small；推理环境 apps/api/embedding_service/.venv。现有 UI 审计修改与 build-qa.md 是用户输入，保留。此次明确替代旧冻结生产资格 spec 中仅云端 Embedding 的假设，但不恢复其生产资格任务。

# Goal

交付由 apps/api 所有的独立、单 CPU 模型进程和可复现下载工具；API/Worker 仅加载 tokenizer，共享内部鉴权模型服务。完成 query/passage 分流、384/64 token 切片、真实本地索引/检索运行入口及验证记录。使用现有 staging/outbox/fence/finalize，始终不自动启用在线问答。

# Non-goals

不配置 Chat、不产生付费请求、不自动开 gate、不宣称服务器验收或人工标注 Recall@5 达标。不生成部署平台定义，不改内容库和媒体所有权，不重开 UI plan，不量化。

# Acceptance criteria

- AC-1: 模型制品固定官方完整 revision 和逐文件 SHA-256；独立锁定 CPU 推理依赖，本地缺失或哈希/身份不符启动失败，离线重启不下载。模型服务单 owner、线程 1、批次 1、并发 1、有限优先队列与有界等待；停机拒绝新请求并完成在途推理。
- AC-2: 内部鉴权 /v1/embeddings 返回有序 384 维有限归一化向量和真实含特殊 token 的 usage，支持 float/base64；拒绝错误模型/维度/批次、无前缀、空白及超过 512 tokens 输入。公开健康仅报告存活，鉴权 readiness 返回固定身份，不泄露秘密。
- AC-3: 仅 E5 适配给 query/passages 添加一次角色前缀并核验服务身份；固定 tokenizer 对正文按 384 tokens、重叠 64 切片，最终含前缀/特殊 token 不超 512，保留源版本/标题定位；完整当前问题优先，历史仅占剩余 token，当前问题超长通过既有 dense_skipped/lexical degraded 路径而非截断或收费失败。pipeline 与模型版本绑定新 generation，其他 provider 保持行为。
- AC-4: 显式本地真实检索入口不需要 Chat，要求独立认证 Qdrant，复用 Worker staging/finalize 安全流程，保留离线演示命令；可运行 smoke、检索与本机测量，文档准确列出实测和未完成阶段，生产默认关闭。

# Risks

Windows 开发机不能代表 2 vCPU/4 GB 目标机；官方模型网络可能不可用。生成的双语回归题只能作为开发回归，不能冒充人工标注验收。制品权重和日志只留忽略目录。在线历史构造遵守瞬态数据边界，不新增 checkpoint 正文。模型新身份不可混入旧 generation；没有目标五进程测量不得放行生产。

# Verification plan

## Verification cases

- AC-1 => M10-E5-ARTIFACT-01
- AC-2 => M10-E5-SERVICE-01
- AC-3 => M09-E5-ADAPTER-01, M10-E5-CHUNK-01, M09-E5-QUERY-01
- AC-4 => M10-E5-LOCAL-01

## Gates

- harness-integrity => AC-1, AC-2, AC-3, AC-4
- api-tests => AC-1, AC-2, AC-3, AC-4
