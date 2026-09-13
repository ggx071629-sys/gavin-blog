---
id: spec-20260913-ubuntu-docker
level: L1
summary: 为独立业务源码仓库提供 Ubuntu 22.04 amd64 容器交付配置
load_when:
  - task:20260913-ubuntu-docker
task_id: 20260913-ubuntu-docker
status: active
verification_profile: focused
planned_modules:
  - M11
documentation_impact: none
documentation_reason: 部署说明随独立 gavin-blog 仓库交付，本控制仓库仅保留规格，不向该仓库上传 Harness 或研发资料。
state_history:
---

# Context

用户已指定 gavin-blog 仅包含业务源码，宿主机 Ubuntu 22.04、x86_64、现有 Nginx，空库安装并计划启用问答。本次仅准备容器交付，不拥有服务器访问或生产资格事实。工作副本为 .run/github-upload/gavin-blog；本机业务数据和既有用户修改不参与。

# Goal

构建 Web/API/E5 镜像定义、Compose 服务和持久化配置、空库初始化、Nginx 片段、无秘密模板及操作说明。

# Non-goals

不改写生产准入，不自动启用问答，不调用付费供应商，不迁移本机数据，不把 Harness、测试产物、秘密或模型权重上传业务仓库。

# Acceptance criteria

- AC-1: Compose 和镜像构建输入仅包含必要源码，固定 amd64，锁定应用依赖并隔离 API 与 E5 环境。
- AC-2: 仅 Web 的 loopback 端口映射到宿主机，数据与 runtime 分卷，Worker 无 runtime 卷；空库初始化可重复执行。
- AC-3: Nginx 保留 HTTPS/同源/SSE/可信 IP 边界，配置默认关闭问答并明确生产资格阻断及 Docker 实测状态。

# Risks

本机无 Docker daemon，不得将静态检查报告为构建或 Ubuntu 实机通过。生产 E5/资格 profile 尚需独立适配，保持 fail-closed。卷操作不得覆盖本机数据库；真实秘密仅在服务器生成，避免进入层、构建参数或 Git。

# Verification plan

## Verification cases

- AC-1 => M11-DOCKER-01
- AC-2 => M11-DOCKER-02
- AC-3 => M11-DOCKER-03

## Gates

- api-tests => AC-1, AC-2, AC-3
