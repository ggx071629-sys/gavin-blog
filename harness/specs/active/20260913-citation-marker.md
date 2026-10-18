---
id: spec-20260913-citation-marker
level: L1
summary: 区分普通文本引用编号与明确的数组代码
load_when:
  - task:20260913-citation-marker
task_id: 20260913-citation-marker
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: none
documentation_reason: 修复内部答案格式校验歧义，不改变公开 API、配置或部署步骤；用行为回归记录边界。
state_history:
---

# Context

See [1] 被空白宽松的数组正则误判，跳过保留引用编号检查。用户要求修复并提交业务 GitHub 仓库；现有 Docker 未提交变更保留本地。

# Goal

普通文本带空白的引用编号必须拒绝；紧邻标识符的数组下标继续支持，带空白数组需明确的单行反引号代码边界。HTML、链接和证据校验保持生效。

# Non-goals

不发布其他待提交改动，不上传测试、Harness、本地数据或秘密；不调整费用或调用真实模型。

# Acceptance criteria

- AC-1: 普通文本保留编号即使具有真实支持引文也返回 structure，不因缺少 supports 偶然通过测试。
- AC-2: 紧凑数组和代码片段中的带空白数组可通过并保持引用渲染；伪造引文、HTML 和链接仍拒绝。

# Verification plan

## Verification cases

- AC-1 => M11-CITATION-MARKER-01
- AC-2 => M11-CITATION-MARKER-02

## Gates

- api-tests => AC-1, AC-2
