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
---
~~~

正文依次包含：Context、Goal、Non-goals、Acceptance criteria、Risks、Verification plan。

