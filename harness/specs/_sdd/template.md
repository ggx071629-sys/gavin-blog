---
id: sdd-template
level: L1
summary: 短生命周期 active spec 的最小模板
load_when:
  - spec-create
author: Gavin
---

# Spec template

新 spec 保存为 `active/YYYYMMDD-short-slug.md`，并包含以下字段与章节：

~~~yaml
---
id: spec-YYYYMMDD-short-slug
level: L1
summary: 一句话目标
load_when:
  - task:YYYYMMDD-short-slug
author: Gavin # optional
task_id: YYYYMMDD-short-slug
status: active
verification_profile: focused # focused | stack | release
state_history:
---
~~~

正文依次包含以下非空 H1 章节：`# Context`、`# Goal`、`# Non-goals`、`# Acceptance criteria`、`# Risks`、`# Verification plan`。

每项验收标准使用唯一标识，格式为 `- AC-1: 可观察结果`。验证计划只引用 `config.toml` 注册的白名单 gate，格式为 `- gate-name => AC-1, AC-2`；每项验收标准至少由一个 gate 覆盖，不能从 Markdown 填写或执行任意 shell 命令。`verification_profile` 选择 `focused`、`stack` 或 `release`，并强制包含该层级在 `config.toml` 注册的最低 gate。

确定性 close 为兼容既有 spec 也接受对应 H2 章节，但新 spec 统一使用上述 H1 结构。Goal 与 Acceptance criteria 缺失或为空时必须先修复 spec，close 不会删除 active 文件或生成不完整归档。

`state_history` 由 Harness 的 freeze/resume 命令维护，新 spec 初始为空。不要手工改写 `status`、冻结元数据或历史记录。

新 spec 必须先提交并存在于 Git HEAD，之后才能开始实现和运行 task verify。
