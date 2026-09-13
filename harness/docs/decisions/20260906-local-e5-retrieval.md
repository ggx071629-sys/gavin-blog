---
id: decision-20260906-local-e5-retrieval
level: L1
summary: 固定本地 E5 CPU 服务、tokenizer 切片与第三方 Chat 的分阶段接入边界
load_when:
  - local-embedding
  - assistant-retrieval
---

# 本地 E5 检索

依据 [本机问答计划](../../../plan-build/local-qa/build-qa.md) 和管理员本轮确认，先在 Windows AMD64 开发机落地，服务器尚未准备好。选用 intfloat/multilingual-e5-small，完整 revision 为 `614241f622f53c4eeff9890bdc4f31cfecc418b3`。模型文件和 tokenizer 的 SHA-256 在 `apps/api/app/local_embedding/model.lock.json`；权重仅下载到忽略目录。独立 `apps/api/embedding_service/uv.lock` 固定 Sentence Transformers、CPU PyTorch 和 tokenizer 依赖。API/Worker 只使用 tokenizers，不加载权重。

推理表示为 `e5-fp32-mean-l2-v1`，采用 attention-mask mean pooling 和 L2 normalization。模型版本由 revision 与表示组成，pipeline 为 `assistant-e5-token384-overlap64-v1`。适配器接受原文，统一添加 query/passage 前缀；原文中恰好含有前缀字符串也视为内容，不移除用户文本。服务只编码已加前缀的输入，不二次添加。单 owner、单推理线程、批次和并发为 1，等待队列最多 8 项，在线 query 优先，默认请求期限 30 秒；超时请求从等待任务中跳过，已运行推理持有唯一 slot 到完成，避免超时后并发模型调用。

切片先沿原 Markdown 标题分段，再按固定 tokenizer 的字符偏移切原文，目标正文 384 tokens、重叠 64 tokens，优先保留换行边界。标题已在 section 正文内；document title/heading/path 作为现有引用 metadata 保留，不隐式追加到编码输入。每片重新编码校验，前缀及特殊 token 计入最终 512 上限。完整当前问题优先，历史仅使用剩余 token；问题超长时不调用模型，沿已有 `dense_skipped` 与 `degraded` 状态继续关键词检索。模型/切片身份不匹配必须重建独立 generation。

`npm run dev:assistant:retrieval -- smoke|rebuild|finalize|query ...` 是明确的真实 Embedding 检索入口，使用 `.env.e5`，无需 Chat。rebuild 使用现有 fenced Worker，止于 ready_to_switch；finalize 以独占 API owner maintenance 运行既有 runtime/content 切换协议，保持 gate disabled。开发演示命令 `npm run dev:assistant` 保持原离线语义。不能在同一个内容库同时运行离线演示与真实检索重建。

当前服务 launcher 仅绑定 loopback 且只支持 development，Bearer 内部鉴权，readiness 只返回非秘密身份。E5 production 在配置层明确拒绝；内部可信 HTTPS 和 qualification profile 扩展留待后续实际部署任务。此决定替代旧冻结生产资格 spec 中仅云端 Embedding 的方案假设，不改写旧历史，也不代表该 spec 已恢复或通过。第三方 Chat 配置以 build-qa 阶段 D 的本机检索验收和容量推算为前置条件，真实供应商、费用预算与数据保留政策由管理员确定。

E5 当前问题超长时，终态回答使用既有字符串 code 字段 `answered_lexical`，并显示“问题较长，本次仅使用关键词检索公开资料”；拒答也附相同提示。复用现有 SSE 字段，不新增协议字段。该布尔状态可进入 checkpoint，问题/历史增强文本仍遵守原有瞬态边界。

2026-09-06 后续决策：管理员已确认 40 条正向题及边界材料人工审核通过，绑定记录见 [评估操作说明](../operations/e5-retrieval-evaluation.md)。管理员另明确要求取消阶段 D 的真实 2 vCPU / 4 GB 共驻验收，改为在本地运行完整进程组、采样资源并反推配置，不预设部署规格。具体采样、内存包络与余量、CPU 核当量和磁盘增长假设以 [阶段 D 测量方法归档](../../../plan-build/local-qa/archive/stage-d.md#method) 为准。该决策时点的部分性能数据不是完整容量报告，当时仍需补测；后续 [阶段 D 测量](../operations/e5-retrieval-evaluation.md) 与 [阶段 F 联调](../operations/local-real-qa.md) 已记录各自完成结果和适用限制。不同硬件性能不按核数线性换算。本轮本机联调和交接无需服务器，实际部署时另处理生产资格适配，当前不修改可执行生产门禁。

官方依据：[E5 固定模型卡](https://huggingface.co/intfloat/multilingual-e5-small/blob/614241f622f53c4eeff9890bdc4f31cfecc418b3/README.md)、[Sentence Transformers CPU 后端](https://sbert.net/docs/sentence_transformer/usage/efficiency.html)。
