---
id: spec-20260908-topic-explorer
level: L1
summary: 首页主题探索用栏目选择驱动多篇笔记展示
load_when:
  - task:20260908-topic-explorer
task_id: 20260908-topic-explorer
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - ui-fix-v2/IMPLEMENTATION.md
documentation_reason: 说明主题探索交互、请求上限和降级行为。
state_history:
---
# Context
用户确认将失去结构表达的知识领域图谱改造为有实际浏览作用的主题探索。
# Goal
栏目选择切换对应最多三篇笔记、摘要与真实阅读链接；默认选中首栏，桌面左右布局，手机上下布局。
# Non-goals
不新增接口，不加载全文到页面载荷，不伪造关系或推荐排序，不扩展为全量知识图谱。
# Acceptance criteria
- AC-1: 最多三个栏目各读取三篇最新文章，保持最多五个文章与分类请求，页面载荷移除全文。
- AC-2: 鼠标和键盘选择栏目后显示对应文章，保留选择；有浏览栏目与全部主题入口，无无效重置。
- AC-3: 读取中、无栏目、空栏目和局部失败区别展示，重试保留有效选择；手机和双主题无横溢。
# Risks
现有文章 API 仍返回全文，单次栏目响应上限由一篇增至三篇；首页只序列化摘要。真实数据不足三篇时不补样例。旧图谱交互测试需更新。
# Verification plan
## Verification cases
- AC-1 => M01-HOME-DATA-01
- AC-2 => M01-HOME-INTERACTION-01
- AC-3 => M01-HOME-STATES-01, M01-HOME-VISUAL-01
## Gates
- web-quality => AC-1
- e2e => AC-2, AC-3
- harness-integrity => AC-1, AC-2, AC-3
