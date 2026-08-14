---
id: archive-20260814-supply-chain-baseline
level: L2
summary: 固定 Python 依赖解析并建立 CI 控制面供应链基线门禁
load_when:
  - task:20260814-supply-chain-baseline
author: Codex
task_id: 20260814-supply-chain-baseline
status: compressed
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/docs/operations/release-readiness.md
  - harness/docs/decisions/20260814-python-lock-and-control-plane.md
documentation_reason: Python 锁定工具、CI 安装合同、控制面供应链不变量及其不可消除的外部限制是长期工程决策
state_history:
---

# 20260814-supply-chain-baseline

Deterministic compressed record. The original active spec remains in Git history.

## Goal

提交通用 Python 锁文件并让 CI 以锁定模式重建 `apps/api/.venv`，同时新增独立、失败关闭的全局供应链基线 check，验证 workflow action 引用、权限、触发器和安装命令没有退回可变或高权限形式。

## Acceptance criteria

- AC-1: `apps/api/uv.lock` 固定项目、dev 与平台相关的完整 Python 依赖解析及来源哈希，并由固定版本 uv 生成；运行时代码直接导入的 `httpx` 属于主依赖而不是 dev-only extra。
- AC-2: CI 使用完整提交 SHA 固定的官方 setup-uv action 与显式 uv 版本，在 `apps/api` 执行 `uv sync --locked --extra dev --python 3.11`，不再动态升级 pip 或用 pip 解析项目依赖。
- AC-3: 新的全局 Harness check 遍历全部 GitHub workflow，拒绝非完整 SHA 的外部 action、`pull_request_target`、超出 `contents: read` 的显式权限、未锁定 Node/Python 安装命令和缺失的锁文件。
- AC-4: 控制面 check 对当前 workflow 与两个锁文件通过，并提供有限、确定性的成功/失败详情，不执行网络请求或修改文件；风险推导的 API gate 从当前执行根的项目 `.venv` 解析 Python，缺失时不退回全局解释器。
- AC-5: 回归测试用隔离 fixture 覆盖安全基线以及可变 action、写权限、危险触发器、`npm install`、`pip install`、非 locked uv 与缺失锁文件。
- AC-6: 验证、发布与决策文档说明 uv 锁定/升级流程、控制面基线、在线漏洞扫描缺口，以及私有 Free 仓库缺少外部 required review 时仍可被同提交修改的限制。
- AC-7: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

## Result

Verified and closed by the harness close command.

## Evidence

[20260814-supply-chain-baseline.json](../../verification/evidence/20260814-supply-chain-baseline.json)

Closed at 2026-08-14T05:23:10.125635+00:00.
