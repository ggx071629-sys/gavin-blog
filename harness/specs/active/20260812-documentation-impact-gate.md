---
id: spec-20260812-documentation-impact-gate
level: L1
summary: 让 active spec 的文档影响在验证和关闭前形成确定性闭环
load_when:
  - task:20260812-documentation-impact-gate
author: Gavin
task_id: 20260812-documentation-impact-gate
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - README.md
  - harness/specs/_sdd/README.md
  - harness/specs/_sdd/template.md
  - harness/workflows/verify.md
  - harness/evolution/policy.md
documentation_reason: Harness 的文档迭代约束、事件边界和操作者流程发生变化。
state_history:
---

# Context

根目录 README 目前只被结构和链接检查覆盖。事件是审计记录，`spec.completed` 不会创建 proposal，也没有任何机制要求一个会改变项目能力或流程的 spec 同步 durable 文档。因此实现可以完成、事件可以产生，而 README 或流程文档仍保持过时。

# Goal

建立可执行的文档影响契约：每个非冻结 active spec 必须声明文档影响；需要更新文档的任务只有在声明目标已于 spec 基线之后提交、证据记录一致且工作区干净时才能验证和关闭。

# Non-goals

- 不自动生成或改写 README、文章、个人资料或其他公开内容。
- 不让 telemetry 直接改变 Agent 行为。
- 不恢复、修改、验证或关闭现有 frozen spec。
- 不引入任意命令执行或 LLM 判定文档语义正确性的机制。

# Acceptance criteria

- AC-1: 非冻结 active spec 必须声明 `documentation_impact`、单行 `documentation_reason`；`required` 必须包含安全的项目相对 Markdown 目标，`none` 不得包含目标。
- AC-2: 既有 frozen spec 无需补充文档影响字段，当前两个 frozen spec 的内容和生命周期状态保持不变。
- AC-3: task verify 对 `required` spec 检查每个目标存在于 HEAD、无未提交变更，并且在 spec 首次进入 Git 的提交之后发生过已提交变更；条件不满足时不执行产品 gate。
- AC-4: schema v2 task evidence 记录规范化的文档影响契约与目标指纹，close 会按当前 HEAD 重新验证契约、完成状态和指纹，过期证据不能关闭任务。
- AC-5: SDD 模板、验证 workflow、演进策略和根 README 说明人工维护边界以及 verify/close 门禁，不再暗示 `spec.completed` 事件会自动触发 README 迭代。
- AC-6: 自动化测试覆盖缺失或非法声明、路径穿越、冻结兼容、目标未更新、目标已更新、未提交漂移和证据漂移。

# Risks

- Git 基线计算错误会让合法任务永久无法关闭，或让旧文档更新被误认为本次任务完成。
- 把 active spec 本身或生成证据当作文档目标会制造自引用循环。
- 将检查错误地应用到 frozen spec 会违反冻结边界。
- 仅能确定目标被提交修改，不能证明文案在语义上充分；语义正确性仍需人工评审。

# Verification plan

- harness-tests => AC-1, AC-2, AC-3, AC-4, AC-6
- harness-integrity => AC-1, AC-2, AC-5
