---
id: operations-e5-retrieval-evaluation
level: L1
summary: 在隔离双语语料上执行本机 E5 检索评估并人工复核标注
load_when:
  - e5-evaluation
  - assistant-operations
author: Gavin
---

# E5 本机检索评估

本工具推进 [build-qa 阶段 D](../../../build-qa.md)。题目及 gold 由 AI 起草，管理员已于 2026-09-06 在当前任务明确确认“人工审核通过”，审核绑定见下文。服务器尚未准备好，阶段 D、生产资格和后续 Chat 配置仍待完成。

## 运行

先按 [API 本机 E5 说明](../../../apps/api/README.md) 启动固定模型服务与 Qdrant，准备忽略配置 `.env.e5`。以下命令从 `apps/api/` 执行；Windows 使用 `.venv/Scripts/python.exe`，POSIX 使用 `.venv/bin/python`。

```powershell
# 不连接服务：校验题集，生成完整原文和逐题标注复核表
.venv/Scripts/python.exe -m app.local_embedding.evaluation --review-only --output data/e5-review-new

# 真实 E5 + Qdrant + 发布 API + Worker + API owner finalize
.venv/Scripts/python.exe -m app.local_embedding.evaluation --env-file .env.e5 --output data/e5-evaluation-new
```

输出目录必须不存在，拒绝覆盖已有运行。每次自动生成两个不同 Qdrant collection 前缀；每种目标语言分别创建 SQLite 内容库、runtime 和媒体目录。通过现有登录/CSRF、文章发布与 Profile API 写入虚构语料，Worker 重建后受控 finalize，并读取 gate 确认 disabled 且无 pending switch。原 `.env.e5` 内容库和真实用户 Profile 均不写入。不会启动在线助手或调用 Chat。

默认题集为 [e5-bilingual-v1.json](../../../apps/api/evaluation/e5-bilingual-v1.json)：每种目标语言 20 篇文章（10 篇相关、10 篇相近干扰）及 1 个虚构 Profile。Profile 必须显式声明，避免默认中文资料混入英文语料；来源按类型与 ID 联合映射。两份语料分开评估，避免同一语料内的等价翻译造成多相关性歧义。共 40 条正向题（四方向各 10 条）及无证据 2 条、术语/代码/混排/超长各 1 条。`--dataset` 可指定同结构题集；此版本只接受明确待复核的草稿状态，不能通过改状态字串伪造人工通过。

## 结果口径

- `review.md`：全部语料、问题、gold 原文、前五名切片与公开路径/版本、逐题复核空栏。
- `results.json`：详细逐题结果，保存在忽略目录。
- `summary.json`：紧凑统计，绑定题集 SHA-256、评估代码 SHA-256、模型/pipeline、两份 generation/collection 及切片/向量集合一致性。
- `failure.json`：未完成测量时明确失败，只包含异常类型，避免泄露供应商配置。已有失败运行保留，重试用新目录。

Recall@5 以检索器返回的前五个 **chunk** 为范围，按相关 **文档集合** 去重：命中的 gold 文档数 / 全部 gold 文档数，再按问题取宏平均。当前每题一个 gold，因此数值等同文档命中率；统计函数支持多个 gold。只将路径和当前公开版本一致的结果计入召回。证据命中另要求 gold 原文完整出现在该文档的返回切片里。向量相似度不作为准确率。

`run_valid` 只表明测量完成、引用有效、没有意外降级；`draft_recall_target_met` 另检查草稿正向集整体 Recall ≥ 0.85。它们都不代表每个边界问题回答正确。无证据问题的 Recall 为 null，近邻只计为 `unsupported_neighbors`；本工具不测 Chat 拒答。超长用例直接测试检索层（可超出公开问答接口输入上限），保留全文并跳过 dense，单独报告关键词降级和证据命中，不混入 40 题正向分数。服务不可用、模型/数据漂移、引用无效、缺失结果或意外降级不会输出有效成功；退出码 1 表示运行无效或草稿 Recall 未达标，0 也不表示阶段 D 通过。

## 本机结果与下一步

2026-09-06，修正评估器默认 Profile 漏登记后，固定题集真实测得整体 Recall@5 与证据命中均为 0.975：中→中、英→英、中→英各 1.0，英→中 0.9。唯一正向漏召回为 `en-zh-queue`（英文询问云雀查询优先级及抢占）；保留失败题，不改题或调参追分。术语、代码、混排命中；6022 tokens 长文本按预期降级但证据命中为 0。两条无证据问题各返回五个近邻，未作为正确答案。完整摘要见 [本机评估 manifest](../../verification/evidence/20260906-e5-retrieval-evaluation.benchmark.json)。

这是规模很小、内容较短、题目与证据共同起草的合成语料结果，存在明显乐观偏差。当前真实快照仅三篇主要中文文章及 Profile，尚不足以验证真实访客的四方向表现。人工审核确认不改变这一覆盖限制。修改题集后需要重新审核与测量，不沿用旧确认或分数。之后还需要真实 2 vCPU / 4 GB 的 Nuxt/API/Worker/Qdrant/模型共驻资源测量，才可继续 Chat 人工配置。

## 人工审核记录（2026-09-06）

- 审核人：本项目管理员（当前任务用户）；确认来源：在收到最终逐题复核材料后明确回复“人工审核通过”。此处记录整版审核确认，不补写未提供的逐题意见。
- 审核范围：`e5-bilingual-v1` 的 40 条正向题、6 条边界用例及已展示的最终本机结果；不扩展为服务器资源验收、真实访客覆盖或 Chat 拒答验收。
- 题集原始文件 SHA-256：`1e9b70059c06ad8bba7df110258ee710ad6404c2c76ec3ff753c2b938a6cd997`。
- 最终材料：`apps/api/data/e5-evaluation-20260906-final/review.md`；SHA-256：`7256326c6193fae958e42b46d7e68f78c8e192f7de8103ac957941475a19135a`。
- 最终运行摘要：同目录 `summary.json`；SHA-256：`81c904f50c9603af3088cdcbf4f3b5abde806abd0dfa9bb309d8cf619d1a207d`。记录确认前已核对题集摘要与最终材料、运行摘要一致；原实测 Recall@5 0.975 不变。

题集、逐题材料和 benchmark 保留测量时的草稿状态，作为历史原始记录；本节是其后发生的人工审核确认。CLI 不读取此确认自动放行，后续重新生成的草稿也不自动继承本次审核。阶段 D 的服务器验收尚未完成，Chat 与生产 gate 继续关闭。

每次运行的数据库、详细结果和 Qdrant 集合都会占用磁盘，不自动清理既有集合。测试集合带 `e5_eval_` 前缀，准确名称记录在 summary；保留需复核的那次运行，清理时只按明确集合名及对应目录进行，不对原内容索引使用通配删除。
