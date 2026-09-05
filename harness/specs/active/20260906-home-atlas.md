---
id: spec-20260906-home-atlas
level: L1
summary: 完成视觉方案第二阶段的真实首页、有限栏目导览及状态验证
load_when:
  - task:20260906-home-atlas
author: Gavin
task_id: 20260906-home-atlas
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-2.md
documentation_reason: 记录首页公开取数、降级、交互和阶段验收边界。
state_history:
---

# Context

阶段一已归档；本任务落实 ui-fix/PROPOSAL.md 第二阶段。当前首页使用四篇文章卡片与孤立名片，没有真实栏目图。现有文章 API 返回全文，taxonomy 返回现存公开栏目与站点总数；无需提前新增接口。实施前版本由首次规格提交的父提交记录。保留已有 UI_AUDIT_REPORT.md 用户修改。

# Goal

以真实作者介绍、有限栏目图、一篇重点文章和紧凑条目完成双主题首页。

# Non-goals

不迁移阶段三至七，不改变 API、发布快照、SEO 路径、后台名片操作或助手准入；不制造技术结构图和在线状态。

# Acceptance criteria

- AC-1: 栏目按 id 升序最多三个，每栏从现有接口取一篇最新公开文章；站点总数直接使用 taxonomy。一次加载最多 taxonomy 一次、栏目单篇三次，另有最近文章四条的一次请求；无栏目时复用最近文章作为回退，无轮询，SSR 不重复携带全文。
- AC-2: 点击或键盘选择栏目可保持选择，悬停和焦点突出关联路径，离开恢复选择，重置清除；链接使用真实栏目 slug 与文章 public_path，说明无需悬停即可阅读。
- AC-3: 空站、有文章无现存栏目、栏目增长、局部读取失败、主要文章读取失败与客户端加载分别呈现；故障不冒充零篇或成功空态。
- AC-4: 作者信息与首屏合组，保留真实资料及联系方式；一篇重点与最多三条紧凑文章，缺摘要不留等高空卡。双主题、320–1440px、短屏、长文本、键盘与减少动态效果可用；测量真实请求量、载荷和生产首屏表现。
- AC-5: 阶段实施文档、首页边界、验证合同与影响计划同步，可追溯到执行证据。

# Risks

分次读取期间发布变化可能使某栏目最新结果为空，需局部明确状态；列表 API 全文可能放大上游流量，即使客户端投影去掉全文也不等于上游变轻。共享名片仅添加首页展示变体，后台默认展示与交互回归。

# Verification plan

## Verification cases

- AC-1 => M01-HOME-DATA-01, M01-HOME-LIVE-01
- AC-2 => M01-HOME-INTERACTION-01
- AC-3 => M01-HOME-STATES-01, M01-P0-02
- AC-4 => M01-HOME-VISUAL-01, M06-PROFILE-CARD-01, M01-HOME-LIVE-01
- AC-5 => M08-DOCS-01

## Gates

- web-quality => AC-1, AC-3, AC-4
- e2e => AC-1, AC-2, AC-3, AC-4
- harness-integrity => AC-5
