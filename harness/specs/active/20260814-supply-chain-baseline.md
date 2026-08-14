---
id: spec-20260814-supply-chain-baseline
level: L1
summary: 固定 Python 依赖解析并建立 CI 控制面供应链基线门禁
load_when:
  - task:20260814-supply-chain-baseline
author: Codex
task_id: 20260814-supply-chain-baseline
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - harness/verification/README.md
  - harness/docs/operations/release-readiness.md
  - harness/docs/decisions/20260814-python-lock-and-control-plane.md
documentation_reason: Python 锁定工具、CI 安装合同、控制面供应链不变量及其不可消除的外部限制是长期工程决策
state_history:
---

# Context

Node CI 已使用带 integrity 的 `package-lock.json` 与 `npm ci`，GitHub Actions 也固定到官方 tag 对应的完整提交 SHA；但 Python CI 仍执行 `pip install -e "./apps/api[dev]"`，会在每次运行重新解析范围依赖，同一 Git 提交可能随索引变化安装不同传递版本。现有 workflow 安全约束主要由同目录静态测试保护，缺少每次 Harness 全局验证都会执行的独立控制面基线 check。

# Goal

提交通用 Python 锁文件并让 CI 以锁定模式重建 `apps/api/.venv`，同时新增独立、失败关闭的全局供应链基线 check，验证 workflow action 引用、权限、触发器和安装命令没有退回可变或高权限形式。

# Non-goals

- 不声称仓库内 check 能抵抗拥有写权限且同时删除 check 的攻击者。
- 不启用部署、发布凭据、第三方扫描 SaaS、自动依赖升级或仓库公开化。
- 不修改 API/Web 业务行为，也不把在线漏洞数据库查询放进确定性 release gate。
- 不上传锁定缓存、虚拟环境或原始依赖安装日志。

# Acceptance criteria

- AC-1: `apps/api/uv.lock` 固定项目、dev 与平台相关的完整 Python 依赖解析及来源哈希，并由固定版本 uv 生成。
- AC-2: CI 使用完整提交 SHA 固定的官方 setup-uv action 与显式 uv 版本，在 `apps/api` 执行 `uv sync --locked --extra dev --python 3.11`，不再动态升级 pip 或用 pip 解析项目依赖。
- AC-3: 新的全局 Harness check 遍历全部 GitHub workflow，拒绝非完整 SHA 的外部 action、`pull_request_target`、超出 `contents: read` 的显式权限、未锁定 Node/Python 安装命令和缺失的锁文件。
- AC-4: 控制面 check 对当前 workflow 与两个锁文件通过，并提供有限、确定性的成功/失败详情，不执行网络请求或修改文件。
- AC-5: 回归测试用隔离 fixture 覆盖安全基线以及可变 action、写权限、危险触发器、`npm install`、`pip install`、非 locked uv 与缺失锁文件。
- AC-6: 验证、发布与决策文档说明 uv 锁定/升级流程、控制面基线、在线漏洞扫描缺口，以及私有 Free 仓库缺少外部 required review 时仍可被同提交修改的限制。
- AC-7: release profile 与最终 change coverage 完整通过，生成当前 schema v2 evidence。

# Risks

- Windows 生成的锁文件若不是通用解析，会漏掉 Linux CI 条件依赖；必须使用 uv 的跨平台项目锁语义并在远端 CI 最终验证。
- uv 工具或 setup action 未同时固定版本与提交，会把一个动态解析缺口替换成另一个可变供应链入口。
- 文本扫描过度拟合单个 workflow 会阻止合法扩展，过度宽松又无法发现降级；检查应基于逐 workflow 不变量并提供 fixture 回归。
- 仓库内策略不是不可变信任根；没有 GitHub 侧强制规则时只能提高可见性和防误改能力。

# Verification plan

- release => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
