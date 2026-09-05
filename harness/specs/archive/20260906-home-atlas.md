---
id: archive-20260906-home-atlas
level: L2
summary: 完成视觉方案第二阶段的真实首页、有限栏目导览及状态验证
load_when:
  - task:20260906-home-atlas
author: Gavin
task_id: 20260906-home-atlas
status: compressed
documentation_impact: required
documentation_targets:
  - apps/web/README.md
  - ui-fix/PHASE-2.md
documentation_reason: 记录首页公开取数、降级、交互和阶段验收边界。
evidence_sha256: b3fd97a793ae267b7b6561e70c7d769365f0ee589d3d14a0e387bea893c8dadd
state_history:
---

# 20260906-home-atlas

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以真实作者介绍、有限栏目图、一篇重点文章和紧凑条目完成双主题首页。

## Acceptance criteria

- AC-1: 栏目按 id 升序最多三个，每栏从现有接口取一篇最新公开文章；站点总数直接使用 taxonomy。一次加载最多 taxonomy 一次、栏目单篇三次，另有最近文章四条的一次请求；无栏目时复用最近文章作为回退，无轮询，SSR 不重复携带全文。
- AC-2: 点击或键盘选择栏目可保持选择，悬停和焦点突出关联路径，离开恢复选择，重置清除；链接使用真实栏目 slug 与文章 public_path，说明无需悬停即可阅读。
- AC-3: 空站、有文章无现存栏目、栏目增长、局部读取失败、主要文章读取失败与客户端加载分别呈现；故障不冒充零篇或成功空态。
- AC-4: 作者信息与首屏合组，保留真实资料及联系方式；一篇重点与最多三条紧凑文章，缺摘要不留等高空卡。双主题、320–1440px、短屏、长文本、键盘与减少动态效果可用；测量真实请求量、载荷和生产首屏表现。
- AC-5: 阶段实施文档、首页边界、验证合同与影响计划同步，可追溯到执行证据。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-home-atlas.json](../../verification/evidence/20260906-home-atlas.json)

SHA-256: `b3fd97a793ae267b7b6561e70c7d769365f0ee589d3d14a0e387bea893c8dadd`

Closed at 2026-09-05T17:54:12.240012+00:00.
