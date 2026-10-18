---
id: spec-20261018-harness-fixture-python
level: L1
summary: 修复隔离 CLI fixture 依赖继承及虚拟环境解释器路径
load_when:
  - task:20261018-harness-fixture-python
task_id: 20261018-harness-fixture-python
status: active
verification_profile: focused
documentation_impact: none
documentation_reason: 恢复既有内部环境定位合同：API 检查使用配置的虚拟环境，临时测试 fixture 使用调用者已锁定依赖。无业务/API、CLI 参数、安装要求或运维步骤变化；不新增永久环境合同或文档目标。
state_history:
---

# Context

前两个任务已正常关闭并上传，当前基线为 f1c262e2；历史 archive、evidence 与 completion event 不变。实际 Linux CI 的 API 测试通过后，六个真实 Harness CLI 测试因临时环境找不到 pytest distribution 失败。已确认 EnvBuilder(system_site_packages=True) 继承基础解释器全局包，不继承调用者 API 虚拟环境。另一个独立缺陷是 collector 对 .venv/bin/python 调用 resolve()，在真实 POSIX 符号链接布局中变成基础解释器，丢失虚拟环境语义。

# Goal

临时 fixture 创建独立虚拟环境，通过只含普通目录行的 .pth 复用调用者已经安装的锁定依赖，不执行网络安装。collector 保留项目 API 虚拟环境解释器的调用路径，避免解引用文件符号链接；原缺失环境检查继续失败关闭。验证既有精确收集、执行、复用、清理、收据与关闭合同以及共享 fixture 的快照前置检查。

# Non-goals

不修改应用业务、API、依赖锁文件或 CI 安装政策，不回退全局解释器，不使用可执行 .pth 代码，不放松依赖指纹、认证收据、隔离、精确身份或缺失环境检查，不连接、操作或部署实际应用服务器，不重写已关闭任务的历史资产。

# Acceptance criteria

- AC-1: 独立临时 fixture 能找到调用者已安装的 pytest 及其 distribution，真实 CLI 选择、复用、失败保留、清理、篡改拒绝与同进程关闭测试保持通过；未选测试不执行，共享 fixture 的提交快照检查仍先于依赖链接与产品执行，不新增网络安装或降低指纹检查。
- AC-2: API Python 为有效符号链接时，collector 与 selected runner 的命令保留虚拟环境调用路径；缺失或断裂环境仍失败关闭。新增确定性回归验证路径语义，原精确选择、禁用/重复拒绝及文件/名称隔离断言保持通过。

# Verification plan

## Verification cases

- AC-1 => M08-IMPACT-SELECTION-01, M08-SNAPSHOT-01
- AC-2 => M08-IMPACT-RUNNERS-01, M08-DOCS-01

## Gates

- harness-tests => AC-1, AC-2
- harness-integrity => AC-1, AC-2
