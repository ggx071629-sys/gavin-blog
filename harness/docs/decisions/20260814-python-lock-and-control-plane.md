---
id: decision-python-lock-and-control-plane
level: L1
summary: 使用 uv 通用锁固定 Python 依赖，并以全局 check 保护 CI 供应链基线
load_when:
  - dependency-change
  - ci-change
  - architecture-decision
author: Codex
---

# Decision: Python lock and CI control-plane baseline

## Status

Accepted.

## Context

API 的 `pyproject.toml` 使用范围约束，过去 CI 每次通过 pip 重新解析传递依赖；同一提交在不同时间可能得到不同环境。Node 已有 lock 与 `npm ci`，Actions 已固定完整提交 SHA，但这些约束只有 workflow 静态测试，没有独立全局 check。

## Decision

- `apps/api/uv.lock` 是 Python 项目、dev extra 与条件平台依赖的唯一提交锁；使用 uv `0.12.4` 生成和检查，registry 保持官方 PyPI。
- 运行时代码直接导入的依赖必须位于主 dependencies；本次将 `httpx` 从 dev extra 移回主依赖，避免生产核心安装缺包。
- CI 固定 setup-uv `v10.0.0` 对应的完整提交 SHA，同时显式请求 uv `0.12.4`，并执行 `uv sync --locked --extra dev --python 3.11`。uv cache 暂不启用，避免大型原生依赖消耗私有 Actions 存储。
- 全局 `supply-chain` check 只读验证全部 workflow 的 action SHA、精确只读权限、危险触发器、锁定安装命令及两个 lock 的 artifact 哈希结构。
- CI telemetry 上传固定 `actions/upload-artifact` v7.0.1 的完整 commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a`。此前 v4.6.2 在 2026-08-14 远端 CI 中触发 Node 20 弃用注解；v7.0.1 官方 `action.yml` 使用 Node 24，上传的脱敏文件、失败语义与 14 天保留边界不变。
- 依赖升级必须显式修改声明、用固定 uv 重新生成 lock、审查 diff，并通过 task release 与最终远端 CI；不得在 CI 自动改写 lock。

## Consequences

- Python CI 从时间相关解析变为由提交内容决定的 locked sync，Linux 条件依赖也包含在 uv 的通用锁中。
- 固定 setup action 与 uv 版本减少工具链漂移；不缓存会增加下载时间，但控制私有仓库存储成本，后续只能通过独立成本证据调整。
- upload-artifact major 升级消除 runner 强制兼容旧 Node runtime 的警告；仍以完整 commit 而非浮动 major tag 作为供应链输入。
- 确定性门禁不查询实时漏洞数据库，因此已锁定依赖仍需人工或单独的非确定性安全审计。
- Starlette 1.6 已对 TestClient 使用旧 `httpx` 发出迁移到 `httpx2` 的弃用警告；当前运行时代码仍直接使用 `httpx`，迁移需独立行为 spec，不能在本供应链任务中静默替换。
- 仓库内 check 只能防误降级并使变更显性化。没有 GitHub 侧 required review/ruleset 时，有写权限的修改者仍能同时更改 check；这不是不可变信任根。
