---
id: operations-release-readiness
level: L1
summary: 本地发布候选门禁、首发阻断项及备份回滚边界
load_when:
  - release
  - operations
  - deployment
author: Gavin
---

# Release readiness

## Current status

项目当前处于“本地 MVP 与工程收口完成、首发准备等待部署决策”。`npm run quality:release` 通过只表示本地发布候选满足代码、契约、测试、构建、可访问性、性能、SEO 和 Harness 完整性门槛；在部署决策及运维演练完成前不得标记为 production-ready。

## Local release candidate gate

从仓库根目录执行：

```powershell
npm ci
npm run quality:release
```

API 虚拟环境必须位于 `apps/api/.venv`，并已安装 `.[dev]`。本地依赖升级后从 `apps/api/` 使用项目固定的 uv 版本重新生成并提交 `uv.lock`，再执行 `uv lock --check --python 3.11`；不得手工编辑锁文件。门禁依次执行 API Ruff、Pytest、Harness check 单测、OpenAPI 快照一致性、Web 类型检查、Vitest、生产构建、axe-core、Lighthouse、核心 Playwright E2E 和 Harness checks。任何一步失败都阻断候选版本。

`quality:release` 在环境变量 `HARNESS_BASE_REF` 存在时，先从 `harness/` 执行 `python -m tools.harness change-check --base <ref> --head <ref>`。该检查只接受同一 Git diff 中的压缩 task archive 与 schema v2 passed evidence，并验证 evidence source commit 位于 base 之后且可从 head 到达。`HARNESS_HEAD_REF` 可选，默认是 `HEAD`。

没有显式基线时，本地 release runner 会清楚报告 change coverage 被跳过。私有 GitHub 仓库 `ggx071629-sys/smart_blog` 的 `Release gate / quality-release` workflow 在面向 `main` 的 pull request、main push 与人工运行中检出完整历史：PR 使用 base SHA，push 使用 before SHA，人工运行使用 HEAD 第一父提交；全零、空、相同或不可解析的 base/head 会在安装依赖前失败。CI 随后以 `npm ci` 安装 Node lock、以固定 SHA 的 setup-uv 安装显式 uv 版本，并在 `apps/api/` 执行 `uv sync --locked --extra dev --python 3.11` 重建 `.venv`；lock 与 `pyproject.toml` 不一致会在 release 前失败。安装 Chromium 后 workflow 只调用权威 `npm run quality:release`，因此远端运行不能进入 local-only coverage skip。

change coverage 会验证 evidence 的 source commit 从 head 可达，所以 squash/rebase 改写已验证提交后不能复用原 evidence；合并策略必须保留验证过的提交。workflow 文件本身只建立可运行 check，不自动证明 GitHub branch protection 或 ruleset 已将其设为 required；必须在首次远端运行出现 check context 后查询仓库规则并单独确认。即使 CI 与 required check 均生效，也只提升合并质量保证，不解除本页的部署、持久化、备份恢复和生产安全 No-Go。

Harness `supply-chain` check 会在每次全局验证中拒绝可变 action、写权限、`pull_request_target`、非锁定安装器与不带 artifact 哈希的 lock 记录；它不执行在线漏洞查询。该仓库当前保持 private，GitHub Free 不提供此前尝试的 required ruleset/branch protection，因此仓库内门禁仍可被拥有写权限且同时修改门禁的人绕过；在升级套餐、公开仓库或迁移到具备等价外部强制能力前，这一限制必须保留为审查风险，不能宣称“不可降级”。

CI 在权威 gate 结束后以 `always()` 生成脱敏 Harness telemetry summary 与 observation-only health，写入 Job Summary，并将仅含这两个 JSON 的 artifact 保留 14 天。原始 JSONL、日志、环境、工作区内容及 `.run/`、`my_image/`、`my_blog_fork/` 不上传；artifact 生成或上传失败会使 job 失败，已有的 release gate 失败也不会被后置步骤覆盖。该短期记录用于人工比较趋势，不是部署证据、自动 Evolution 输入或 production-ready 证明，并会消耗私有仓库 Actions 存储配额。

## Before first production release

- 通过独立 spec 确定 Web/API 运行拓扑、域名、TLS、进程管理和部署平台。
- 为 SQLite 指定持久卷、单写者约束、备份频率、保留周期及恢复目标。
- 为媒体目录选择持久本地卷或对象存储适配器，并验证数据库与媒体的一致恢复点。
- 在目标环境配置随机管理员密码、Secure Cookie、精确 CORS 来源、公开 API 地址与 canonical 站点地址。
- 在最终 HTTPS 边缘响应验证 `Strict-Transport-Security`；应用为本地 HTTP 保持不设置 HSTS，不能用本地响应代替公网边缘检查。
- 验证公网 HTML 保留应用的 CSP Report-Only、`X-Frame-Options`、`nosniff`、Referrer-Policy 与 Permissions-Policy；收敛字体和其他资源来源后，另行评审并启用强制 CSP。
- 在生产数据副本或等价空库上执行 `alembic upgrade head`，验证迁移链和 FTS5 可用性。
- 完成一次备份恢复演练和一次上一版本回滚演练，记录耗时与人工步骤。
- 从干净检出使用锁文件安装依赖并通过 `npm run quality:release`。
- 确认 Git 工作树干净，生成带版本号和 commit SHA 的发布说明。

## Data boundaries

`.env`、开发日志、SQLite 数据库、本地媒体和原始验证产物不得进入 Git。备份必须同时覆盖内容事实库 SQLite 与媒体对象，并包含其中的 index-embedding 账本；只有数据库或只有媒体的备份不构成可恢复备份。`assistant_runtime` 数据库及其 WAL/SHM、checkpoint 和临时副本明确排除于长期备份。恢复演练须先重建空 runtime schema，公开 Chat／query 至少锁到下一个北京时间零点，Qdrant 丢失时须先按 Worker 账本重建 generation 再签发新的 readiness receipt。

北京时间每日 2.00 元人民币只约束按部署价格快照计算的公开 Chat 新调用；query Embedding 与 index Embedding 使用各自独立 cap，三者都以 `settled + reserved` 计算，也都不是供应商总账单保证。已越过 sending 的失 fence调用仍按价格快照无正文保守结算，异常 usage 可以更高。第四阶段 archive/evidence 只证明当时形式关闭；第五阶段本地运营控制面与 release evidence也不等于已合并、上线、对访客开放或 production Go。启用前必须分别检查 API capability、Web launcher、runtime gate 与当前 generation readiness，在 `checkpoints`/`writes` 零残留后签发 receipt，再由管理员显式 enable；generation finalize 会先 fail closed，切换后必须重签 receipt。真实供应商、反向代理 SSE、备份恢复、目标服务器公网安全与 2 vCPU／4 GB 实机验收仍是生产放行条件。

`.run/`、`my_image/` 和复刻项目快照 `my_blog_fork/` 永久排除于 smart_blog Git 历史与 CI checkout；不得通过强制添加、归档上传或 workflow artifact 绕过该边界。

## Rollback boundary

在部署方案确定前，本项目只定义回滚原则，不虚构平台命令：保留上一可运行应用产物；迁移前创建可验证备份；数据库迁移默认前向修复，只有迁移显式证明可逆时才执行降级；涉及数据库或媒体写入的回滚必须先停止写流量并保护当前副本。

## Go / no-go

只有上述首发条件全部有可复查证据时才能作出 Go 决策。当前结论为 **No-Go for production deployment**，但可以继续生成和验证本地 release candidate。
