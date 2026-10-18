# 阶段 A–C：本地 E5 实施归档

归档日期：2026-09-06。状态：已完成。仅在追溯环境、模型服务、索引实施或早期设计差异时读取；不作为当前待办。
返回 [主计划](../build-qa.md)。

## 已完成事项

- [x] 阶段 A：开发机 Windows AMD64 已确认，独立 spec `20260906-local-e5-retrieval` 已建立；管理员确认服务器尚未准备好。
- [x] 阶段 B：固定 revision 模型下载、逐文件 SHA-256 和独立 CPU 服务本机部署；中英文真实 smoke 与官方 pooling 参考对比通过。
- [x] 阶段 C（本机）：E5 角色适配、token 切片、真实检索 CLI 已实施；独立内容快照 generation 14 含 20 个切片/向量，受控 finalize 后 gate disabled。真实发布/改版/删除、模型禁止外网重启和 Qdrant 重启检索验证通过；20 项精确合同测试通过。

证据：[实施 manifest](../../../harness/verification/evidence/20260906-local-e5-retrieval.benchmark.json)；[E5 决策](../../../harness/docs/decisions/20260906-local-e5-retrieval.md)。

## 原实施要求

以下保留实施时的要求和完成条件；命令的当前使用方式以 [API 操作说明](../../../apps/api/README.md) 为准。

### 阶段 A：环境确认与实施规格

1. 检查本地机的 OS、CPU 型号/架构、物理核与逻辑核、内存、磁盘、现有进程和模型下载网络。
2. 本地机承担功能验收和资源测量，部署配置作为测量后的推算输出；不要求事先准备服务器，不将配置估算写成已部署事实。
3. 建立 spec；明确模型服务由 `apps/api` 所有、单进程约束、内部鉴权、超时、队列、资源限制和停机行为。
4. 确定唯一目标平台后再编写相应启动/部署文件；保持现有内容库、媒体和无关用户改动。

完成条件：实施 spec 和影响计划齐备，运行平台及本地模型存放位置明确。

### 阶段 B：下载并启动本地 Embedding 服务

1. 从官方 Hugging Face 仓库下载模型，锁定完整 commit revision；同时固定 tokenizer、配置和所用权重文件。
2. 记录来源、revision、文件 SHA-256、依赖锁和推理实现版本。权重放在被忽略的本地数据目录或外置模型卷，不提交 Git；不依赖浮动 `main` 或运行时自动下载。
3. 使用独立的推理依赖环境，安装 CPU 版本依赖；服务只加载一次模型。设置本地文件加载，模型缺失或身份不符时启动失败。
4. 实现内部 `POST /v1/embeddings`：支持现有客户端的 `model`、字符串数组 `input`、`dimensions=384`；返回有序 `data[index].embedding`、模型身份和真实 tokenizer 统计的 usage。检查 SDK 默认 `encoding_format` 的实际请求，支持并测试所需编码形式。
5. 非 384 维请求、超长输入、非法内容和过大批次明确报错；不得静默截断或伪造 token 用量。`prompt_tokens` / `total_tokens` 的口径必须包含实际编码输入，并可复现。
6. 实现健康/就绪探测与内部身份核验，确认模型 revision、维度、前缀方案、池化和归一化版本。健康信息不暴露秘密。
7. 初始服务并发设为 1、批次设为 1、推理线程从 1 开始测量；API 与 Worker 的总并发由服务端统一限流。限制等待队列，在线查询优先于批量索引。
8. 服务绑定内部地址并鉴权。开发环境可用 loopback HTTP；生产通过可信证书的内部 HTTPS 接入，保留证书验证和现有生产校验。

完成条件：无需 Chat 凭据即可独立执行 Embedding smoke check；中英文输入均得到有限数值、384 维、归一化向量；断网重启仍能加载模型。

### 阶段 C：接入双语检索并重建索引

1. 在模型专属客户端适配中统一处理角色：查询编码加 `query: `，文档编码加 `passage: `，中英文一致。通过显式方法分流，前缀只添加一次；服务端不再重复添加，其他模型适配不受影响。
2. 使用模型定义的 attention-mask mean pooling 和 L2 normalization；以官方参考实现验证服务输出。
3. 按固定 tokenizer 切片，初始正文目标 384 tokens、重叠 64 tokens；包含标题等实际附加内容、前缀和特殊 token 后，最终输入必须不超过 512 tokens。保留段落、标题、源版本和引用定位信息。
4. 查询先保留完整当前问题，再在剩余 token 预算内加入历史。当前问题本身超限时明确处理，不截掉问题尾部；是否采用既有 lexical degraded 路径由 spec 明确，并对用户和诊断状态保持可区分。
5. 修改切片、前缀、权重或推理表示时更新 pipeline/model version。新建 384 维 generation，重算已发布内容向量，不复用或混合旧维度、旧模型向量。
6. 复用既有 fenced Worker、outbox、staging 和 finalize 机制。Worker 只准备 `ready_to_switch`；API owner 完成切换，gate 保持关闭，重新生成所需 readiness。
7. 在尚无 Chat 凭据时，通过独立索引/检索验证入口验收；不提前打开在线问答 gate。保留关键词检索及现有受控降级语义。
8. 增加显式真实模型开发启动配置与使用文档；现有离线演示命令保持原语义，界面和日志准确区分运行模式。

完成条件：持久索引可重建、可重启恢复；发布/修改/删除可通过 Worker 更新；查询确实调用本地 E5，且引用仍指向正确公开版本。

## 编写方案时的差异记录

以下是编写方案时核对的现状，不是待实施功能的完成声明。

| 当前入口 | 现状与实施要求 |
| --- | --- |
| `apps/api/app/assistant/providers.py` | 已有真实 Chat / Embeddings 适配。当前基础 query 方法复用 documents 方法，E5 接入必须显式区分两种角色 |
| `apps/api/app/assistant/graph.py` | Chat 使用 `json_schema`、`strict=True` 和原始响应；供应商需要通过实际兼容性验证 |
| `apps/api/app/assistant_index/chunker.py` | 当前按字符切片；不能把既有 800 字符直接当作 512 tokens 内的输入 |
| `apps/api/app/assistant_index/embeddings.py` | 真实 Embedding 路径要求独立、带认证的 Qdrant，不能直接沿用离线嵌入式存储 |
| `apps/api/app/assistant/validation.py` | 生产环境要求模型 endpoint 使用 HTTPS，并校验资格、预算和身份绑定 |
| `scripts/run-assistant-dev.mjs` | 会明确选择离线测试 provider；仅修改 `.env` 不会把此命令变成真实模型模式 |

本方案新增模型服务进程、依赖和切片行为。开始编码前执行 Harness intake/specify，建立独立 SDD spec，明确所有权、影响范围和验证用例；不要重开已完成的 UI 主 plan。平台未选定前不生成 `infra/`、`deploy/` 或平台服务定义。
