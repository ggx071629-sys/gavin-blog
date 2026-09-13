---
id: archive-20260906-e5-retrieval-evaluation
level: L2
summary: 为本机 E5 提供可重现的四方向检索评估、待人工复核题集与证据
load_when:
  - task:20260906-e5-retrieval-evaluation
task_id: 20260906-e5-retrieval-evaluation
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/operations/e5-retrieval-evaluation.md
documentation_reason: 增加独立验收入口、Recall口径、语料审核和本机/正式资格区别，需保留可复现操作说明。
evidence_sha256: 8193e53915e634d582d06ac42f10d505009bed409e5fdf2c97f638eb119db1d4
state_history:
---

# 20260906-e5-retrieval-evaluation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

准备40条四方向正向问题（每向10条）及无证据、术语、代码、混排、长文本用例。两份独立目标语言语料都包含相关文档和干扰文档，使用既有真实 E5、Qdrant、发布投影、Worker、finalize和检索器；评估输出Recall@5、证据片段命中、公开版本一致性、按方向分组及明确未验收项。输出可供管理员复核的本地题集/结果文档。

## Acceptance criteria

- AC-1: 严格校验题集唯一ID、语言方向、正向gold文档及证据原文、40题方向覆盖与边界case；AI草拟状态显式保留，缺失/伪造引用不能进入测量。生成可阅读的人工复核材料。
- AC-2: 评估在新建独立目录和唯一Qdrant collection前缀中，通过API发布、真实Worker重建及API owner finalize生成两种目标语言的持久语料；不触及原库，已有输出目录拒绝覆盖，Chat和gate保持关闭。
- AC-3: Recall@5按相关文档集合计算，另报告gold证据片段命中和当前发布版本/公开路径匹配；不重复计算同一文档的多个chunk。检索降级、无证据近邻和超长问题明确报告，不能以cosine分数或无证据有返回认定通过。
- AC-4: CLI可重现运行并写紧凑统计及本地详细结果；报告绑定dataset digest、模型/pipeline/generation，服务失败或漂移不输出成功；永不自动判定阶段D或生产通过。README与build-qa如实更新人工复核/目标机待办。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-e5-retrieval-evaluation.json](../../verification/evidence/20260906-e5-retrieval-evaluation.json)

SHA-256: `8193e53915e634d582d06ac42f10d505009bed409e5fdf2c97f638eb119db1d4`

Closed at 2026-09-06T10:02:22.132877+00:00.
