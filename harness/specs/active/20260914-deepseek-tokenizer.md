---
id: spec-20260914-deepseek-tokenizer
level: L1
summary: 固定官方 V4.1 分词器并部署离线 Chat 长度计数
load_when:
  - task:20260914-deepseek-tokenizer
task_id: 20260914-deepseek-tokenizer
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 记录分词器版本、离线部署和保守计数边界。
state_history:
---

# Context

生产 deepseek-flash 使用 DeepSeek-V4.1-Flash。首次请求因 LangChain 回退下载 cl100k_base 等待约 64 秒。用户授权部署官方匹配分词器并同步 ggx071629-sys/gavin-blog；现有博客、数据、有限验证约束及累计 2 元真实 Chat 验证预算继续保留。

# Goal

固定官方 V4.1 tokenizer.json 的提交与哈希，通过 LangChain custom_get_token_ids 离线加载；生产初始化验证制品，构建镜像预置文件。保留 UTF-8 保守上界、Chat wire 协议和 E5 分词器。同步纯代码、许可与构建配置，秘密、内容和原始证据不上 GitHub。

# Non-goals

不更改消息模板、证据截取策略、模型、预算或回答质量规则；不新增常驻进程，不做长期压测。

# Acceptance criteria

- AC-1: 固定官方制品可离线计数，中英文、代码和特殊字符可重现；缺失或损坏在生产初始化时失败且不联网回退。
- AC-2: LangChain 计数使用官方 V4.1 文件，完整请求继续保守估算，已有输入和输出约束不放宽。
- AC-3: 服务器新容器离线计数通过、问答和博客可用，GitHub 保存可复现构建及回滚说明，不含秘密或业务数据。

# Verification plan

## Verification cases

- AC-1 => M11-V41-TOKENIZER-01
- AC-2 => M11-V41-TOKENIZER-02
- AC-3 => M11-V41-TOKENIZER-03

## Gates

- api-tests => AC-1, AC-2
- api-lint => AC-1, AC-2
- e2e => AC-3
