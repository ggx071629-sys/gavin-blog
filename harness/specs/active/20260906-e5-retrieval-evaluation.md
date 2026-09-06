---
id: spec-20260906-e5-retrieval-evaluation
level: L1
summary: 为本机 E5 提供可重现的四方向检索评估、待人工复核题集与证据
load_when:
  - task:20260906-e5-retrieval-evaluation
task_id: 20260906-e5-retrieval-evaluation
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/operations/e5-retrieval-evaluation.md
documentation_reason: 增加独立验收入口、Recall口径、语料审核和本机/正式资格区别，需保留可复现操作说明。
state_history:
---

# Context

接续 build-qa.md 阶段 D；用户确认服务器尚未准备好。A–C 本机实现已关闭。现有公开快照只有三篇主要中文文章与 Profile，不能伪称覆盖英文目标语料。新工具与题集用于本机开发回归，题集由 AI 起草，人工确认和服务器测量均不由本任务虚构。

# Goal

准备40条四方向正向问题（每向10条）及无证据、术语、代码、混排、长文本用例。两份独立目标语言语料都包含相关文档和干扰文档，使用既有真实 E5、Qdrant、发布投影、Worker、finalize和检索器；评估输出Recall@5、证据片段命中、公开版本一致性、按方向分组及明确未验收项。输出可供管理员复核的本地题集/结果文档。

# Non-goals

不启动服务器部署、Chat配置或付费调用，不修改原内容库/媒体，不给AI草拟标注盖人工确认章，不把无相关内容的向量近邻当作正确答案，不更换模型或调参追逐此题集。

# Acceptance criteria

- AC-1: 严格校验题集唯一ID、语言方向、正向gold文档及证据原文、40题方向覆盖与边界case；AI草拟状态显式保留，缺失/伪造引用不能进入测量。生成可阅读的人工复核材料。
- AC-2: 评估在新建独立目录和唯一Qdrant collection前缀中，通过API发布、真实Worker重建及API owner finalize生成两种目标语言的持久语料；不触及原库，已有输出目录拒绝覆盖，Chat和gate保持关闭。
- AC-3: Recall@5按相关文档集合计算，另报告gold证据片段命中和当前发布版本/公开路径匹配；不重复计算同一文档的多个chunk。检索降级、无证据近邻和超长问题明确报告，不能以cosine分数或无证据有返回认定通过。
- AC-4: CLI可重现运行并写紧凑统计及本地详细结果；报告绑定dataset digest、模型/pipeline/generation，服务失败或漂移不输出成功；永不自动判定阶段D或生产通过。README与build-qa如实更新人工复核/目标机待办。

# Risks

小型人工可读语料不代表真实访客分布；题目和gold同时由AI起草存在偏差。两种语言语料分开以避免等价翻译的多相关性混淆；结果只支持该固定语料。未来在真实语料增加英文发布内容后仍需独立验收。原文/详细日志留忽略目录，只提交紧凑manifest。检索层始终给近邻，不承担Chat无证据拒答。

# Verification plan

## Verification cases

- AC-1 => M10-EVAL-DATASET-01
- AC-2 => M10-EVAL-ISOLATION-01
- AC-3 => M10-EVAL-METRICS-01
- AC-4 => M10-EVAL-REPORT-01

## Gates

- api-tests => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-1, AC-2, AC-3, AC-4
