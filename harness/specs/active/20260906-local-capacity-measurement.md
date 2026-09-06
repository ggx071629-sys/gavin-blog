---
id: spec-20260906-local-capacity-measurement
level: L1
summary: 本机隔离完整进程组测量并推算部署资源
load_when:
  - task:20260906-local-capacity-measurement
task_id: 20260906-local-capacity-measurement
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - build-qa.md
  - harness/docs/operations/e5-retrieval-evaluation.md
documentation_reason: 新增可复现本机资源测量入口、口径及真实容量结果。
state_history:
---

# Context

用户要求开始执行已更新的 build-qa。人工题集审核已确认；阶段 D 的剩余项为本地完整进程组测量和容量推算，不要求服务器。已有本地 E5/Qdrant 和其他开发进程继续运行，必须区分受测进程与背景负载。

# Goal

提供显式本机测量命令，Windows 每秒采样 Nuxt 构建预览、API、Worker、Qdrant、模型及子进程，覆盖冷启动、稳态、近512token、重建重叠及CPU限制敏感性场景。API通过独立 development-only 测量入口调用真实检索器，不调用Chat。隔离语料扩大规模以观察重建；不将其当新的人工检索质量集。产出紧凑资源manifest和带余量的内存/CPU/磁盘推算。

# Non-goals

不修改生产路由或qualification，不改原库、旧集合、既有进程或原始人工审核证据；不安装服务器、不付费调用Chat、不把推算当云端保证或长期耐久压测。

# Acceptance criteria

- AC-1: 采样统计按进程身份和实际时间差求CPU核当量，内存区分同步峰值/峰值之和；估算声明OS缓存和余量，缺少角色/场景/计数器或异常运行不得伪造有效容量结果。
- AC-2: 启动仅接受全新隔离目录、development且online关闭；新端口冲突拒绝启动，测量API鉴权，原应用无测量路由；仅关闭本轮启动的进程，保护源库和旧服务。
- AC-3: 真实五角色负载完成，记录样本数、时长、输入规模、延迟/错误、重建重叠、CPU亲和性、后台内存/换页与磁盘项；报告绑定代码、模型、语料和generation，机器检查和实际测量分开，后续Chat完整链路开销明确待补。

# Verification plan

## Verification cases

- AC-1 => M10-CAPACITY-METRICS-01
- AC-2 => M10-CAPACITY-ISOLATION-01
- AC-3 => M10-CAPACITY-REPORT-01

## Gates

- api-tests => AC-1, AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
