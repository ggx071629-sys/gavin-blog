# 方案边界与维护参考

读取条件：当前任务涉及架构、数据发送、部署边界或回滚时，只读取对应章节。此文件不维护阶段进度。
返回 [主计划](../build-qa.md)。

<a id="scope"></a>
## 已确定的方案

采用 **`intfloat/multilingual-e5-small` 本地 CPU 推理 + 第三方 OpenAI-compatible Chat API**。

先在本地完成 Embedding 下载、项目接入、索引重建、双语检索验收和资源测量，推算部署配置，再引导管理员人工配置第三方 Chat；最后在本地进行真实问答联调并修订资源估算，形成部署交接材料。

这里的“云端 Chat 部署”指在第三方平台开通模型服务并配置 API 接入，本机只运行客户端及本地 Embedding。部署机配置由本地实测反推，不预设 2 vCPU / 4 GB。第三方供应商、具体 Chat 模型和凭据在人工配置阶段确定。

| 项目 | 确定选择 |
| --- | --- |
| Embedding 模型 | `intfloat/multilingual-e5-small`，中文、英文及跨语言检索 |
| 向量维度 / 输入上限 | 384 维；每条输入最多 512 tokens，含前缀和特殊 token |
| 推理部署 | 同机独立服务、单模型进程、CPU；API 与 Worker 通过内部接口共用 |
| 初始推理实现 | Sentence Transformers + CPU PyTorch，FP32 基线；依赖单独隔离并锁定 |
| 资源优化条件 | 本地 FP32 测量显示资源或延迟需要优化时，验证 ONNX / INT8；通过精度回归后才能替换 |
| 接口 | 保持现有 OpenAI-compatible Embeddings / Chat Completions 适配边界 |
| 向量存储 | 同机独立单节点 Qdrant，认证访问、持久化；内容事实仍在 SQLite |
| Chat 编排 | 复用现有 LangChain `ChatOpenAI`、LangGraph 和引用校验 |
| 离线开发 | 保留 `npm run dev:assistant` 的现有离线演示模式；另设显式真实模型启动方式 |
| 本轮交付 | 本地真实问答联调、资源实测与部署配置推算；实际部署另行安排，现有生产 gate/readiness 合同不因估算而自动通过 |

阶段 E 的连接配置现已填写，普通调用已验证；具体当前状态以主计划和当前任务为准。

<a id="data"></a>
## 调用链与数据边界

```text
索引：已发布内容 → Worker → token 切片 → 本地 E5 服务 → Qdrant 新 generation
查询：浏览器 → 同源 API → 本地 E5 服务 → 向量 + 关键词混合检索
回答：检索证据 + 用户问题 + 必要历史 → 第三方 Chat → 引用校验 → 浏览器
```

- Embedding 服务由 API 应用负责集成，但作为独立进程运行，避免 API 与 Worker 各加载一份模型。
- 浏览器不直连模型服务或 Qdrant；Chat API Key 只保存在后端秘密配置中。
- 本地 Embedding 下载完成后可离线推理；真实 Chat 仍需要运行客户端的本机访问第三方网络。
- Chat 会向供应商发送问题、必要历史及选中的公开内容片段；上线前确认其数据保留政策。Embedding 本地化不等于整个问答链路完全离线。
- 继续使用现有内容可见性、发布版本、删除失效、引用和预算约束。

<a id="rollback"></a>
## 回滚与持续维护

- 故障时优先通过既有运营 gate 停止新问答，按当前 fence/清理流程处理在途任务。
- 保留可用的模型制品与 generation 信息；模型、tokenizer、切片规则、推理实现和向量索引作为配套版本管理。
- 回滚不能只替换模型文件。使用既有受控切换/重建流程恢复匹配的 generation，确认发布版本有效性，并重新满足 readiness。
- 第三方换模型、改价格、换 endpoint 或模型别名发生变化时，重新校验兼容性与资格绑定。
- ONNX / INT8 的导出、量化来源和质量结果进入版本记录；不将量化视为无需验收的透明替换。

<a id="sources"></a>
## 依据

- [E5 官方模型卡](https://huggingface.co/intfloat/multilingual-e5-small)：384 维、512 tokens、query/passage 前缀、池化与归一化方法。
- [官方权重文件](https://huggingface.co/intfloat/multilingual-e5-small/blob/main/model.safetensors)：页面列出的 FP32 safetensors 约 471 MB；此数字不是部署总磁盘或进程内存需求。
- [Sentence Transformers 推理优化文档](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)：CPU 后端、ONNX 与量化方案；实际收益需要目标硬件测量。
- [项目架构边界](../../../harness/docs/architecture/boundaries.md)、[SDD 规则](../../../harness/specs/_sdd/README.md)、[API 配置示例](../../../apps/api/.env.example)：现有进程、数据、模型接入和生产资格约束。

## 生产资格边界

旧冻结生产资格任务未恢复，其可执行生产合同留待实际部署专项处理，不阻塞本轮本机联调。平台未确定前不生成平台专属部署文件；本机容量推算不能当成部署或生产资格通过。
