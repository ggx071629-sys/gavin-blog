---
id: spec-20260809-soften-light-signal-color
level: L1
summary: 以低饱和批注紫替换浅色主题中过于突兀的酸柠檬信号色
load_when:
  - task:20260809-soften-light-signal-color
author: Gavin
task_id: 20260809-soften-light-signal-color
status: verified
---

# Context

Electric Editorial 浅色主题当前使用 `#bcf200` 作为全站 `--ee-signal`，覆盖选中文本、装饰线、强调边框、选中态和部分按钮。该酸柠檬色在接近白色的画布上饱和度过高，压过正文与钴蓝主色。深色主题中的同类高亮仍与夜间界面匹配，不属于本次问题。

# Goal

将浅色主题信号色改为低饱和“批注紫”，降低视觉刺激，同时保留 Electric Editorial 的明确批注感、交互可见性和无障碍对比度。

# Non-goals

- 不改变深色主题的信号色。
- 不改变主色、状态色、排版、布局、圆角或组件结构。
- 不为单个组件引入新的原始颜色值或旁路设计令牌。
- 不重新定义成功、警告、危险和信息语义。

# Acceptance criteria

1. 浅色主题 `--ee-signal` 使用 `#8878c0`，`--ee-signal-ink` 使用 `#171326`。
2. 深色主题继续使用 `--ee-signal: #c7f300` 与现有 signal ink，不发生回归。
3. 浅色信号色与 `#f8f9fa` 画布达到至少 `3:1` 对比度；信号色与 signal ink 达到至少 `4.5:1`。
4. 全站现有 signal 消费者通过语义令牌自动更新，不新增组件级 raw palette 值。
5. 浅色与深色首页在桌面、移动视口均无 axe 违规或横向溢出。

# Risks

- 紫色过浅会让边框与选中态失去可辨识度；候选色必须满足非文本对比度下限。
- 紫色过深会让深色文字失去可读性；配套 signal ink 必须满足正文对比度下限。
- 信号色在多种组件中复用，单点令牌替换可能暴露个别过度依赖饱和度的组件，需要首页质量场景覆盖主要公开消费者。

# Verification plan

- 先增加设计令牌与对比度单元测试，确认现有酸柠檬令牌会失败。
- 修改浅色主题的两个语义令牌，不触碰深色主题。
- 运行目标单测、全量 Web 单测、类型检查与生产构建。
- 运行首页双主题、双视口质量场景，检查 axe 与横向溢出并生成视觉证据。
- 运行 `python -m tools.harness verify 20260809-soften-light-signal-color`。
