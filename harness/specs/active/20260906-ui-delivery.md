---
id: spec-20260906-ui-delivery
level: L1
summary: 修复全站集成发现的写作预览无障碍缺陷并验证发布候选
load_when:
  - task:20260906-ui-delivery
author: Gavin
task_id: 20260906-ui-delivery
status: active
verification_profile: release
verification_escalation: 用户指定第七阶段全站交付明确要求发布候选门禁，除局部无障碍修复外执行完整 release 检查。
documentation_impact: required
documentation_targets:
  - ui-fix/PHASE-7.md
documentation_reason: 记录集成缺陷、全站验证、默认关闭产物、恢复版本及不能由自动化抵扣的设备验收缺口。
state_history:
---

# Context

用户要求完成 UI 提案第七阶段。基线 d64b5f7 的完整 release 在生产写作台初始 Markdown 状态捕获 critical aria-valid-attr-value：预览按钮指向 v-if 尚未创建的元素。第六阶段实体手机验收仍待完成，工程修复与整体阶段完成分别记录。

# Goal

保持写作区受控目标稳定存在、预览正文仍按需创建，完成原有全量发布候选门禁和交付记录。

# Non-goals

不改变保存/发布协议、数据、主题、依赖或测试断言阈值；不部署、不启用公开助手；不以模拟 IME 或视口证明真机验收。

# Acceptance criteria

- AC-1: 三类新建和编辑页面初始 Markdown 状态及预览切换后，每个写作区域按钮的 aria-controls 均指向存在的唯一元素；预览内容按需创建，正文输入保留，隐藏预览不暴露重复内容。
- AC-2: 原有完整 release 门禁通过，包括生产页面无障碍矩阵和 Lighthouse 四项 90 门槛；全站业务回归、默认关闭和实际隔离问答保持，失败记录不被隐去。
- AC-4: 完整串行 release 的监督预算由 900 秒提高至 1200 秒以容纳实测约 15 分钟的前序步骤及助手组；保留原有超时终止、所有测试和质量阈值。
- AC-3: 阶段七文档记录真实覆盖、检查结果、默认关闭候选与恢复边界；第六阶段真机缺口保持待验收，不宣称生产资格或全阶段已完成。

# Risks

直接把整个预览从 v-if 改成 v-show 会提前挂载 Markdown/Mermaid 等内容，增加初始开销；只保留空容器，内部 slot 继续按需渲染。完整门禁发现其他缺陷时继续按实际范围修复，不放宽规则。旧集成断言需与已迁入的首页/关于文案、连续条目和深色代码容器一致；恢复仅验证本测试目标，不要求共享隔离库的全部回收站为空。代码测量使用实际不透明背景并覆盖语法 token 对比度。

# Verification plan

## Verification cases

- AC-1 => M02-DESK-LAYOUT-01, M07-UNIT-SITE-QUALITY-01
- AC-2 => M07-UNIT-SITE-QUALITY-01, M01-UNIT-CODEBLOCK-THEME-01, M01-UNIT-PUBLIC-EXPERIENCE-01, M02-UNIT-ARTICLE-LOOP-01, M07-UNIT-THEME-STRUCTURE-01, M09-UNIT-ASSISTANT-01, M09-UI-INTERACTION-01
- AC-3 => M08-DOCS-01
- AC-4 => M08-IMPACT-SELECTION-03, M08-IMPACT-EXECUTION-04

## Gates

- e2e => AC-1, AC-2
- web-quality => AC-1, AC-2
- harness-integrity => AC-3
- harness-tests => AC-4
- release => AC-1, AC-2, AC-3, AC-4
