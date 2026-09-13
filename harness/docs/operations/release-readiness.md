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

项目当前处于公开问答 `LOCAL_READY` 和整站 production No-Go。`npm run quality:release` 通过只表示本地发布候选满足代码、契约、测试、构建、可访问性、性能、SEO 和 Harness 完整性门槛；它不证明真实供应商、最终 TLS／SSE 链、目标 2 vCPU／4 GB、恢复或监控。原资格任务已于 2026-09-06 按管理员要求取消并移除 spec，后续生产资格需重新立项。配置声明的批准非秘密 profile、匹配的 pinned public-key set 与签名 manifest 均未落盘；唯一平台部署 artifact、真实目标 47 项 case 记录也不存在。因此当前既不是有效 `QUALIFICATION_NO_GO`，也不是 `QUALIFICATION_GO_CANDIDATE`。

资格状态只允许 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO`。前者要求所有必测 case 为 pass；后者要求真实 measured fail 及其无环 `blocked_by` 因果链完整，不能用 missing／unknown／没环境代替。task close 只关闭这次资格判定；只有仍新鲜的 GO candidate 才可由管理员在任务外继续 `FINAL_GO → PUBLIC_ENABLED`。部署、runner、readiness 和 close 均不得自动开启 Web launcher、API capability 或 runtime gate。

## Local release candidate gate

从仓库根目录执行：

```powershell
npm ci
npm run quality:release
```

API 虚拟环境必须位于 `apps/api/.venv`，并已安装 `.[dev]`。本地依赖升级后从 `apps/api/` 使用项目固定的 uv 版本重新生成并提交 `uv.lock`，再执行 `uv lock --check --python 3.11`；不得手工编辑锁文件。门禁依次执行 API Ruff、Mypy、Pytest、Harness check 单测、OpenAPI 快照一致性、Web 类型检查、Vitest、生产构建、axe-core、Lighthouse、核心与默认关闭助手的 Playwright E2E，以及 Harness checks。任何一步失败都阻断候选版本。

`quality:release` 在环境变量 `HARNESS_BASE_REF` 存在时，先从 `harness/` 执行 `python -m tools.harness change-check --base <ref> --head <ref>`。该检查只接受同一 Git diff 中的压缩 task archive 与 schema v2 passed evidence，并验证 evidence source commit 位于 base 之后且可从 head 到达。`HARNESS_HEAD_REF` 可选，默认是 `HEAD`。

没有显式基线时，本地 release runner 会清楚报告 change coverage 被跳过。私有 GitHub 仓库 `ggx071629-sys/smart_blog` 的 `Release gate / quality-release` workflow 在面向 `main` 的 pull request、main push 与人工运行中检出完整历史：PR 使用 base SHA，push 使用 before SHA，人工运行使用 HEAD 第一父提交；全零、空、相同或不可解析的 base/head 会在安装依赖前失败。CI 随后以 `npm ci` 安装 Node lock、以固定 SHA 的 setup-uv 安装显式 uv 版本，并在 `apps/api/` 执行 `uv sync --locked --extra dev --python 3.11` 重建 `.venv`；lock 与 `pyproject.toml` 不一致会在 release 前失败。安装 Chromium 后 workflow 只调用权威 `npm run quality:release`，因此远端运行不能进入 local-only coverage skip。

change coverage 会验证 evidence 的 source commit 从 head 可达，所以 squash/rebase 改写已验证提交后不能复用原 evidence；合并策略必须保留验证过的提交。workflow 文件本身只建立可运行 check，不自动证明 GitHub branch protection 或 ruleset 已将其设为 required；必须在首次远端运行出现 check context 后查询仓库规则并单独确认。即使 CI 与 required check 均生效，也只提升合并质量保证，不解除本页的部署、持久化、备份恢复和生产安全 No-Go。

Harness `supply-chain` check 会在每次全局验证中拒绝可变 action、写权限、`pull_request_target`、非锁定安装器与不带 artifact 哈希的 lock 记录；它不执行在线漏洞查询。此前远端检查记录为 private 仓库，所用套餐下未能启用 required ruleset／branch protection；这是当次观察，仓库可见性、套餐和规则是否仍相同需在发布时重新查询。仅凭本地 workflow 或历史查询不能宣称远端强制保护已生效；没有独立强制保护时，拥有写权限且同时修改门禁的人仍可绕过仓库内规则。

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

后续重新立项并推进生产资格前，管理员必须批准并提交配置所指向的非秘密 profile 与匹配的 pinned public-key set；versioned case suite 已在仓库中。下文任务 ID 与 manifest 路径对应既有工具配置，不代表仍有同名开放 spec；新任务应先明确其配置绑定。完成一次真实目标判定后，仓库再保存签名的 `harness/verification/qualifications/20260830-public-qa-production-qualification.json`。原始 case observation、summary、provider probe ledger、重型日志、抓包、数据库副本、原问答、IP、私有 endpoint、provider raw payload 和 private key 均留在批准的 Git 外加密存储。

`python -m tools.harness qualification-verify 20260830-public-qa-production-qualification` 校验签名、schema、源码／artifact／profile／case-suite 绑定、TTL、目标与 provider 事实、完整 case 终态和三开关关闭；缺失或过期都非零。历史 manifest 到期不拖垮未来普通本地 release，但永远不能授权 `FINAL_GO`。

### Qualification CLI contract

以下命令已经存在，但原任务已取消，且管理员尚未批准完整生产 profile／平台／真实供应商与目标主机；命令可用不等于资格可执行，更不产生占位 No-Go。后续新任务明确配置绑定并提交批准的非秘密输入后，先从 `apps/api/` 用 lock 一致的环境完成 profile 检查；真实 provider probe 必须同时显式选择 Chat 与 Embedding，并把 ledger/output 写在 profile 批准的 qualification root：

```powershell
uv run --locked python scripts/assistant_qualification.py schema
uv run --locked python scripts/assistant_qualification.py validate "<approved-profile-path>"

uv run --locked python scripts/run_assistant_provider_qualification.py `
  --profile "<approved-profile-path>" `
  --approve-profile-digest "sha256:<approved-64-hex-digest>" `
  --ledger "<approved-qualification-root>/provider-ledger.json" `
  --output "<approved-qualification-root>/provider-probe.json" `
  --chat `
  --embedding

uv run --locked python -m app.assistant.provisioning
uv run --locked python -m app.assistant.readiness `
  --probe-live `
  --qualification-profile "<absolute-approved-profile-path>" `
  --provider-probe "<absolute-reviewed-provider-probe>"
```

前两个 profile 命令不部署也不调用供应商。provider probe 是显式、按批准 calls/micro-CNY envelope 计量的真实调用；最终 readiness 要求同一份 probe 中 Chat 与 Embedding 都存在且通过，并要求环境已选择相同 profile/digest/probe hash。命令中的占位符没有仓库默认值，不能把示例摘要、配置自报身份或本地替身当成真实结果。

目标 evidence runner 本身不执行 47 个 case；操作者按 versioned suite 的 `depends_on` 顺序在目标环境执行检查、复核 Git 外原始产物，再从 `harness/` 逐项追加 observation：

```powershell
$taskId = "20260830-public-qa-production-qualification"
$artifactManifest = "<approved-immutable-deployment-artifact-manifest>"
$workspace = "<profile-approved-off-repo-qualification-root>/run-<id>"

python -m tools.harness qualification-run-init $taskId `
  --artifact $artifactManifest `
  --workspace $workspace

# 每次调用只登记一个已经执行并复核的 case；不得覆盖已有记录。
python -m tools.harness qualification-run-record `
  --workspace $workspace `
  --observation "<reviewed-case-observation.json>"

python -m tools.harness qualification-run-assemble `
  --workspace $workspace `
  --summary "<reviewed-qualification-summary.json>" `
  --output "<unsigned-compact-manifest.json>"

python -m tools.harness qualification-sign `
  --input "<unsigned-compact-manifest.json>" `
  --private-key "<approved-secret-source-private-key.json>" `
  --output verification/qualifications/20260830-public-qa-production-qualification.json

python -m tools.harness qualification-verify $taskId
```

`qualification-run-init` 要求当前 tracked source 干净、最终不可变 artifact manifest 存在、workspace 位于 profile 声明的 `qualification_root` 下且完全在 Git checkout 外，并自动绑定当前 commit、profile、case suite 和真实 2 vCPU／4 GB 目标观测。每份 case observation 的字段必须精确为：

```text
schema_version: 1
case_id: <versioned suite 中的 case ID>
status: <pass | measured_fail | blocked_by:CASE-ID>
reviewer: <至少 2 个字符的复核者>
reviewed_at: <不早于 run start、带 offset 的 ISO-8601 时间>
artifact_records:
  - artifact_id: <稳定且非空的 ID>
    kind: <非空产物类型>
    path: <Git 外已存在且已复核的原始文件绝对路径>
    location_category: <encrypted-off-host-object-store | encrypted-off-host-filesystem>
    retention_days: <大于等于 1 的整数>
    reviewed: true
```

每个 case 至少一条 artifact record；runner 读取文件并计算 SHA-256，不接受 Git 内路径。记录是 append-only；依赖尚未记录时拒绝，依赖失败后的 case 只能引用 suite 祖先中已经 `measured_fail` 的 blocker，不能把 missing/unknown 伪装为 No-Go。

assemble 前必须完整记录 suite 当前定义的全部 47 个 case。summary 顶层字段精确为 `schema_version`、`completed_at`、`provider`、`active_generation`、`switches`、`qualification_usage`、`results`、`operator`，嵌套合同如下；所有价格、维度、模型、generation 和 envelope 必须来自批准 profile 或已复核观测，不能从本文占位符推导：

- `provider`：精确包含 `real_provider`、`chat`、`embedding`。Chat 字段为 `provider/model/version/model_identity_source/input_price_micro_cny_per_million/output_price_micro_cny_per_million/reports_usage/reports_finish_reason`；Embedding 字段为 `provider/model/version/model_identity_source/dimension/input_price_micro_cny_per_million/reports_usage`。identity source 只接受 `provider-response`、`versioned-provider-contract`、`operator-declaration`；自报 identity 或缺 usage/finish reason 不能让 `provider_contract` 通过。
- `active_generation`：精确包含 `id/collection/dimension/distance/pipeline_version`，与 profile 的 collection prefix、维度和 pipeline 一致，distance 必须为 `Cosine`。
- `switches`：精确包含 `before/canary/after/runner_auto_enabled`；before/after 的 `web_launcher/api_capability/runtime_gate` 全为 false，canary 的 `edge_restricted/administrator_enabled` 全为 true，runner auto-enable 为 false。
- `qualification_usage`：精确包含唯一非空的 `beijing_dates`，三类调用计数、`total_micro_cny`、与 profile 完全一致的 `max_calls/max_micro_cny` 及 `within_envelope: true`；调用或费用越界会拒绝。
- `results`：必须且只能包含 `profile_validation`、`deployment`、`provider_contract`、`tls_proxy`、`qdrant`、`backup_restore`、`saver`、`resources`、`conformance`、`observability`、`dark_launch`。每项精确包含 `status/case_ids/summary`，case ID 非空且唯一，summary 至少 12 个字符，状态必须能由所连 case 证明。
- `operator`：精确包含 `reviewer/reviewed_at/decision_reason/residual_risks/remediation_tasks`；review 在 qualification completion 之后。`QUALIFICATION_NO_GO` 必须给出非空 remediation task 引用，缺失输入不能借此分类。

签名私钥不是 PEM，而是只存在于批准 secret source 的 JSON 文件，字段精确为 `schema_version/key_id/algorithm/n/e/d`：schema 为 1，算法为 `rsa-sha256-pkcs1-v1_5`，`e` 为 65537，RSA 至少 3072 位，`n/d` 使用 base64url。仓库中的 public-key set 字段精确为 `schema_version/keys`，每个 key 为 `key_id/algorithm/n/e/not_before/not_after`；签名程序不会替操作者生成或 pin key。任何命令都不得把 key 值、raw endpoint、真实问答、IP 或 provider raw payload 写进参数、Git 或 compact manifest。runner、签名和 verify 都不会自动开启 Web launcher、API capability 或 runtime gate；`qualification-verify --historical` 只供历史审计，不能授权 `FINAL_GO`。

本地备份 helper 的实际接口如下；snapshot 目录必须全新，restore 的内容库、媒体和 runtime 目标也必须全新且不得覆盖 live 路径：

```powershell
uv run --locked python scripts/run_assistant_backup_restore.py snapshot `
  --destination "<fresh-snapshot-directory>"
uv run --locked python scripts/run_assistant_backup_restore.py verify `
  --snapshot "<snapshot-directory>"
uv run --locked python scripts/run_assistant_backup_restore.py restore `
  --snapshot "<snapshot-directory>" `
  --database "<fresh-content-database>" `
  --media "<fresh-media-directory>" `
  --runtime "<fresh-runtime-database>"
```

该 helper 能验证本地 fenced snapshot 与 fresh-target restore，但不产生主机外加密回执，不能单独证明 profile 要求的最终备份资格。

## Data boundaries

`.env`、开发日志、SQLite 数据库、本地媒体和原始验证产物不得进入 Git。备份必须同时覆盖内容事实库 SQLite 与媒体对象，并包含其中的 index-embedding 账本；只有数据库或只有媒体的备份不构成可恢复备份。`assistant_runtime` 数据库及其 WAL/SHM、checkpoint 和临时副本明确排除于长期备份。恢复演练须先重建空 runtime schema，公开 Chat／query 至少锁到下一个北京时间零点，Qdrant 丢失时须先按 Worker 账本重建 generation 再签发新的 readiness receipt。

北京时间每日 2.00 元人民币只约束按部署价格快照计算的公开 Chat 新调用；query Embedding 与 index Embedding 使用各自独立 cap，三者都以 `settled + reserved` 计算，也都不是供应商总账单保证。已越过 sending 的失 fence 调用仍按价格快照无正文保守结算，异常 usage 可以更高。第四阶段 archive/evidence 只证明当时形式关闭；第五阶段本地运营控制面已经进入当前代码，release evidence 也只证明本地门禁，二者都不等于已上线、对访客开放或 production Go。启用前必须分别检查 API capability、Web launcher、runtime gate 与当前 generation readiness，在 `checkpoints`/`writes` 零残留后签发 receipt，再由管理员显式 enable；generation finalize 会先 fail closed，切换后必须重签 receipt。真实供应商、反向代理 SSE、备份恢复、目标服务器公网安全与 2 vCPU／4 GB 实机验收仍是生产放行条件。

`.run/`、`my_image/` 和复刻项目快照 `my_blog_fork/` 永久排除于 smart_blog Git 历史与 CI checkout；不得通过强制添加、归档上传或 workflow artifact 绕过该边界。

## Rollback boundary

在部署方案确定前，本项目只定义回滚原则，不虚构平台命令：保留上一可运行应用产物；迁移前创建可验证备份；数据库迁移默认前向修复，只有迁移显式证明可逆时才执行降级；涉及数据库或媒体写入的回滚必须先停止写流量并保护当前副本。仓库已提供共同写 fence、SQLite online backup、版本化媒体 manifest 和隔离恢复校验，但本地 snapshot 明确没有主机外加密回执，不能冒充最终备份演练。

## Go / no-go

只有上述首发条件全部有可复查证据时才能作出 Go 决策。当前结论为 **No-Go for production deployment**，但可以继续生成和验证本地 release candidate。
