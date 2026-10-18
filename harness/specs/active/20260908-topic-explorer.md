---
id: spec-20260908-topic-explorer
level: L1
summary: 首页恢复笔记、领域和文章之间的知识路线
load_when:
  - task:20260908-topic-explorer
task_id: 20260908-topic-explorer
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - plan-build/ui-refinement/IMPLEMENTATION.md
documentation_reason: 说明主题探索交互、请求上限和降级行为。
state_history:
---
# Context
用户要求沿用原先知识路线，不做总汇总。恢复根节点、领域分支与文章之间的可视关系。
# Goal
桌面展示我的笔记 → 领域 → 最新文章，手机纵向分支。悬停与键盘焦点突出路线，选择保持，明确提供领域与文章链接。
# Non-goals
不新增接口，不加载全文到页面载荷，不伪造关系或推荐排序，不扩展为全量知识图谱。
# Acceptance criteria
- AC-1: 最多三个栏目各读取一篇最新文章，保持最多五个文章与分类请求，页面载荷移除全文。
- AC-2: 鼠标和键盘选择领域后突出对应分支并保留选择；提供浏览领域与阅读文章入口，仅有选择时展示查看全部路线按钮。
- AC-3: 读取中、无栏目、空栏目和局部失败区别展示，重试后清除旧选择；手机和双主题无横溢。
# Risks
不推断文章间或先修知识关系；每个领域仅展示最新发布入口，维持原有请求边界。低对比连线在选中时加深，文字不透明淡出。
# Verification plan
## Verification cases
- AC-1 => M01-HOME-DATA-01
- AC-2 => M01-HOME-INTERACTION-01
- AC-3 => M01-HOME-STATES-01, M01-HOME-VISUAL-01
## Gates
- web-quality => AC-1
- e2e => AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
