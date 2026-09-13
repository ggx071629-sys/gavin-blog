---
id: spec-20260913-docker-assistant
level: L1
summary: 补齐 Docker 中 E5 和 DeepSeek 的生产适配并进行限额真实验证
load_when:
  - task:20260913-docker-assistant
task_id: 20260913-docker-assistant
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: required
documentation_targets:
  - apps/api/README.md
documentation_reason: 生产 E5 的 TLS 与 profile 绑定及 DeepSeek 输出合同需要维护者可见说明。
state_history:
---

# Context

用户要求 Ubuntu 22.04 x86_64 容器交付包含可用问答，已安装 Docker，并批准本次真实 Chat 累计最多 2 元。当前 E5 拒绝生产、profile 并发下限与单 owner E5 冲突、DeepSeek 适配仅限开发。真实域名及服务器资源未提供，本机演练不能冒充服务器资格。

# Goal

保留配置绑定、TLS、费用账本、引用验证和管理员开关，补齐 E5 与 DeepSeek 的生产能力；部署输入使用空卷、秘密不进 Git，执行隔离验证。

# Non-goals

不迁移本机业务数据、不使用 development 绕过生产限制、不替用户声明未知服务器事实、不公开部署、不上传 Harness 或测试产物。

# Acceptance criteria

- AC-1: 生产 E5 仅接受固定模型与单并发、明确 TLS 信任和 profile 绑定，旧 profile 摘要保持兼容。
- AC-2: DeepSeek 在生产使用显式 JSON 输出合同与应用严格校验，保留 usage 和无自动重试，探测不谎称供应商原生 schema 保证。
- AC-3: Docker 配置提供必要证书、配置挂载与初始化流程；隔离验证使用真实模型时累计费用不超过 2 元，证据与秘密保持本地。

# Risks

不得用模拟资格 profile 证明真实服务器批准。未知 usage 保守预占；所有重试也计入本次总额。API/Worker 不加载模型权重，不共享 runtime 数据库。

# Verification plan

## Verification cases

- AC-1 => M11-DOCKER-ASSISTANT-01
- AC-2 => M11-DOCKER-ASSISTANT-02
- AC-3 => M11-DOCKER-ASSISTANT-03

## Gates

- api-tests => AC-1, AC-2, AC-3
