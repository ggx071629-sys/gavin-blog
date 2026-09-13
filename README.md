---
id: project-readme
level: L1
summary: Gavin 个人技术博客的公开介绍与当前建设状态
load_when:
  - public-project-overview
author: Gavin
---

# Gavin

Gavin 是一个面向未来自己的个人知识库，也是一张面向招聘与合作的技术名片。项目用于沉淀技术文章、问题排查、项目复盘、阶段总结和读书笔记，并以数字笔记／技术刊物的方式公开呈现。

博客代码由三个部分组成：[前端 `apps/web`](apps/web/README.md)、[后端 `apps/api`](apps/api/README.md) 和 [接口契约 `packages/contracts`](packages/contracts/README.md)。问答助手、数据库读写和媒体管理属于后端；前端负责公开页面、管理后台和问答界面。`harness/` 与 `plan-build/` 是配套研发资料。

## 项目状态

| 范围 | 当前状态 |
| --- | --- |
| 核心内容系统 | 公开阅读与管理员创建、保存、预览、发布、回收站闭环已实现 |
| 管理与体验 | 写作台、账号改密/恢复/会话管理、关于页修订、双主题及响应式页面已实现；阶段记录见 [实施资料](plan-build/README.md) |
| 本机问答 | 离线开发和真实 E5/Qdrant/Chat 两种入口已实现；支持文章、项目、读书、公开名片、合格关于页修订和简历来源 |
| 公开问答生产资格 | 本机接入不等于生产资格；默认关闭，显式本机真实模式可启用，生产 profile 与目标证据仍需独立验收 |
| 生产部署 | 按当前[发布准备说明](harness/docs/operations/release-readiness.md)保持 **No-Go**，未完成目标上线资格 |

仓库提供发布候选质量门禁；门禁存在、历史任务通过或代码已提交，都不代表当前提交通过了所有检查。即使本地发布候选检查通过，也不等于满足生产上线条件。生产问答的 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO` 与任务外 `FINAL_GO → PUBLIC_ENABLED` 边界见 [发布准备](harness/docs/operations/release-readiness.md)，本机运行状态需读取实际配置与服务状态。

## 核心能力

- 公共站点：文章、读书笔记、项目、归档、关于与全站搜索
- 稳定内容地址：`/notes/{year}/{month}/{slug}`、`/books/{year}/{month}/{slug}`、`/projects/{slug}`
- 单管理员工作台：Session 登录、草稿、自动保存、预览、发布、回收站和个人资料管理
- 账号安全：固定管理员账号、邮件验证码改密/找回、登录会话查询与撤销；安全邮箱与公开名片邮箱独立
- 关于页内容：写作台草稿—预览—发布管理 About 专属文案，公开页只读当前发布修订
- 内容组织与发现：栏目、标签、SQLite FTS5、公开引用、wikilink 与反向链接
- 发布完整性：文章、项目、读书和关于页使用发布快照；文章与关于页提供版本历史、差异和回滚界面
- 媒体与可移植性：拖放／粘贴上传、WebP/AVIF 转换、外链登记、Markdown ZIP 导出和安全草稿导入
- 阅读体验：GFM、代码高亮、目录、脚注、提示块、Mermaid、KaTeX、深浅主题和响应式布局
- 内容发现输出：canonical、Open Graph、JSON-LD、RSS、站点地图与 `robots.txt`
- 安全与质量：HttpOnly Cookie、CSRF、防登录暴力尝试、类型检查、单元／端到端测试、axe-core 与 Lighthouse 门禁
- 公开问答：入口由 Web 开关、后端可用性和公开路径共同决定；支持带引用回答、结果恢复与会话清除，浏览器不持久化问答正文或幂等材料。启用 Web 开关后会先读取可用性，用户打开面板后才创建会话；清除只描述本站数据处理，不能撤回供应商已收到的数据
- 资料来源：站长主动发布且具备资格的关于页修订可参与问答，默认 seed 和 Web 模板静态文字不因此获得资格；简历首次/换址自动入队，同址替换 PDF 后显式刷新，引用指向当前有效版本附件
- 问答运营：`/admin/assistant` 提供可用性概览、费用与总预算、同步任务、独立管理试问、紧急停止、索引重试/重建/finalize。预算修改受部署授权上限约束，页面刷新不调用模型或 Qdrant 探活

## 产品边界

- 当前是单管理员个人博客，不提供公共注册、评论系统、站内分析或联系表单。公开问答默认关闭；本机真实接入及历史验证不等于公网开放或 production Go，目标供应商、反向代理 SSE、持久化和备份恢复仍须验收。
- 内容 SQLite 保存发布内容、修订、认证、简历版本、索引账本及统一预算策略；短会话、Chat/query 账本和 checkpoint 位于独立问答运行库。媒体通过存储适配器管理，Qdrant 只保存可重建派生向量。
- 受支持的浏览器访问路径是同源 `/api/v1`；认证 Session 由 API 管理，Web 不持有登录令牌。
- 本地开发不依赖 Docker；生产基础设施尚未选型，不在当前能力范围内。

## 架构与仓库地图

应用源码及数据归属如下；详细模块说明由三个目录各自的 README 维护。

```text
apps/
├── web/                 # 前端：公开页面、写作台、问答界面及同源代理
└── api/                 # 后端：业务、认证、问答、存储与索引 Worker
    ├── app/             # API 和业务实现
    └── data/            # 本机默认数据目录，Git 忽略
packages/
└── contracts/           # OpenAPI 与派生 TypeScript 类型
```

运行关系如下。助手相关进程和模型依赖由显式模式启用，不代表已获得生产资格。

```text
Browser
   │  same-origin /api/v1
   ▼
Nuxt 4 + Nitro
   │  server-side proxy
   ▼
FastAPI（启用助手时为唯一 API owner）
   ├─ content SQLite + FTS5 + Alembic
   ├─ media storage adapter
   └─ assistant API（default-off）
      ├─ assistant_runtime SQLite（短会话／账本／checkpoint，不进长期备份）
      ├─ content SQLite assistant FTS5 + Qdrant（可重建派生向量）
      └─ Chat + query Embedding（本机真实模式使用 DeepSeek + E5）

Index Worker（独立进程、default-off）
   └─ content SQLite outbox／index ledger ──► index Embedding ──► Qdrant

E5 Service（本机真实模式的独立模型进程）
   └─ 为 API query 与 Index Worker 提供内部 Embeddings 接口
```

| 路径 | 职责 |
| --- | --- |
| [`apps/web/`](apps/web/README.md) | Nuxt SSR、公共页面、管理界面与同源 API 代理 |
| [`apps/api/`](apps/api/README.md) | FastAPI、认证、业务规则、内容/runtime SQLite、迁移、媒体存储与独立索引 Worker |
| [`packages/contracts/`](packages/contracts/README.md) | `/api/v1` OpenAPI 快照与派生类型；不是独立运行服务 |
| `harness/` | 产品基线、架构决策、SDD/VDD 规格、验证与紧凑证据 |
| [`plan-build/`](plan-build/README.md) | 按主题归集的实施计划、阶段记录、设计资料与测试报告 |
| `scripts/` | 本机启动器、问答开发/检索入口和发布候选门禁 |
| `.github/workflows/` | GitHub Actions 发布候选检查 |

根 npm workspace 只包含 Web 与 Contracts；API 是独立的 Python 项目。更细的责任约束见 [架构边界](harness/docs/architecture/boundaries.md)。

从 `apps/api/` 启动普通 API 时，内容库默认 `data/gavin.db`，媒体默认 `data/media`，可分别由 `GAVIN_DATABASE_URL` 和 `GAVIN_MEDIA_ROOT` 指定。真实问答开发模式还读取 `.env.e5` 的内容库配置，不能假定所有模式共用默认库；其运行库为 `data/assistant-local-real/assistant_runtime.db`。离线问答的 runtime 使用临时目录。数据库和媒体是运行数据，不是接口契约的一部分。

## 本地开发

Windows 本机已配置好环境后，可直接双击根目录的 [启动项目.cmd](启动项目.cmd)：自动启动或复用 E5、Qdrant，随后启动真实问答 API 与 Web，准备完成后打开 `http://127.0.0.1:3101`。重复双击会复用同一个启动实例。双击 [停止项目.cmd](停止项目.cmd) 关闭该入口启动的进程；原先独立运行的依赖服务不受影响，模型、数据库、索引和预算账本保留。

停止窗口会保留结果，按任意键关闭；自动化可设置 `GAVIN_LAUNCHER_NO_PAUSE=1` 免暂停，退出码仍反映成功或失败。启动失败时窗口同样保留说明。快捷入口只管理自己创建的进程，不能关闭测试或其他终端启动的服务。本机 Chat 成功记录签名有效且配置匹配时，年龄不阻止运行或重启；启动显示最后验证时间，超过 24 小时仅作提示。缺失或无效证据仍拒绝，按 [API 本机探测步骤](apps/api/README.md) 处理；不修改时间戳、不删除原账本，也不会自动发起付费 Chat 资格探测；真实模式中的主动提问仍受模型费用与预算约束。

快捷入口使用现有 `.env`、`.env.e5`、模型环境和 Qdrant 存储，不安装依赖、不下载模型，也不会自动执行付费 Chat 资格探测。Chat 签名验证记录须仍有效；配置缺失、证据无效或端口冲突会在窗口中显示原因。运行状态与日志保存在 `.run/quick-start/`，仅本机可访问。完整配置前提见 [本机真实问答说明](apps/api/README.md#本机真实问答阶段-f)。

当前发布候选参考环境为 Node.js 22（至少 22.19）、Python 3.11 和 uv 0.12.4；本地开发不要求 Docker。从仓库根目录安装 Web 依赖和浏览器测试所需的 Chromium，再配置 API：

```powershell
npm ci
npx playwright install chromium

cd apps/api
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# 将 .env 中的 GAVIN_ADMIN_PASSWORD 替换为长随机密码

uv sync --locked --extra dev --python 3.11
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

升级 2026-08-26 之前创建的数据库时，执行 `alembic upgrade head` 前必须同时备份 SQLite 数据库与媒体目录；迁移 `20260826_0020` 会不可逆地删除已废弃子系统表。全新数据库可直接迁移。

另开一个终端，在仓库根目录启动 Web：

```powershell
npm run dev:web
```

- Web：`http://localhost:3000`
- API：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/api/health`
- OpenAPI UI：`http://127.0.0.1:8000/docs`

Web 默认配置已经匹配以上地址；需要覆盖时，将 `apps/web/.env.example` 复制为 `apps/web/.env`。API 面向开发与部署操作者的示例配置见 `apps/api/.env.example`；只允许测试夹具设置的内部启动开关不属于该清单。

### 本地问答功能开发

三个入口用途不同，均从仓库根目录执行：

| 命令 | 用途与数据范围 |
| --- | --- |
| `npm run dev:assistant` | 离线问答，确定性 test provider；问答 runtime 与派生向量临时保存 |
| `npm run dev:assistant:real` | 真实 E5/Qdrant/Chat 问答，使用已配置内容库和持久问答 runtime；需要有效本机验证记录 |
| `npm run dev:assistant:retrieval -- smoke` | 只检查本地检索链路，不生成 Chat 回答 |

真实模式和 E5/检索操作前提见 [API 说明](apps/api/README.md#本机真实问答阶段-f)。以下说明针对离线问答入口：

完成上述依赖安装并把 `apps/api/.env` 保持为 `GAVIN_ENVIRONMENT=development` 后，可从仓库根目录用一个命令启动已集成到真实项目页面的问答功能：

```powershell
npm run dev:assistant
```

该命令在 `http://127.0.0.1:3101` 启动 Web、在 `http://127.0.0.1:8101` 启动 API，并读取 `apps/api/.env` 指向的现有内容 SQLite 与媒体配置。启动时先验证 development 环境和本机配置，通过后才迁移内容库，再为当前已发布内容重建进程内问答索引；右下角「问 Gavin」使用本地离线、带引用的确定性回答器，不读取真实 Chat／Embedding 密钥，也不会把问题发送给云端模型。短会话 runtime、签名密钥和向量存储只存在于本次启动的临时目录或内存，停止后清理。

这是开发审计入口，不是生产启用路径。普通 `npm run dev:web` 仍默认不显示问答入口，production 也拒绝该离线替身。启动期间新发布或修改内容后需重启此命令，才能把新的 outbox 事实重建进当前内存索引。按 `Ctrl+C` 会停止两个子进程；端口冲突时可用 `GAVIN_ASSISTANT_DEV_WEB_PORT` 和 `GAVIN_ASSISTANT_DEV_API_PORT` 覆盖两个回环端口。

## 验证与生成命令

| 命令 | 用途 |
| --- | --- |
| `npm run test:web` | 运行 Web Vitest 单元测试 |
| `npm run build:web` | 运行 Web 生产构建 |
| `npm run test:e2e` | 启动隔离的 API/Web 测试服务，核心通过后运行受控助手专用 Playwright 套件 |
| `npm run quality:web` | 运行类型、lint、单测、构建、无障碍、Lighthouse 与故障态检查 |
| `npm run quality:release` | 运行完整本地发布候选门禁 |
| `npm run contracts` | **重新生成** `packages/contracts/openapi.json` 和 `api-types.d.ts`，需已准备好的 API 虚拟环境 |

API 可独立检查：

```powershell
cd apps/api
uv run ruff check .
uv run pytest
```

`quality:release` 依次覆盖 API lint 与测试、Harness 测试、OpenAPI 与派生类型一致性、Web 质量门禁、核心与受控助手 E2E，以及 Harness 完整性。测试套件会自行管理隔离端口，不需要预先启动开发服务。Contracts 生成不会自动改写 Web 的存量手写消费模型，接口变化仍需核对实际类型与 parser。

## 规格、验证与 CI

协作时先读 [AGENTS.md](AGENTS.md)，再由 [Harness 索引](harness/INDEX.md) 路由到必要的产品、架构、规格和工作流文档。涉及行为、API、数据、安全或跨栈边界的变更按 SDD/VDD 执行；不要把根 README 当成权威细节的副本。

本地 `quality:release` 只有在设置 `HARNESS_BASE_REF` 时才会验证风险变更与 schema v2 evidence 的覆盖关系；未设置时属于 local-only 模式。GitHub Actions 在面向 `main` 的 pull request、`main` push 及人工触发时使用 Git 基线运行同一门禁。工作流文件存在不代表远端检查已经通过，也不证明仓库已强制 required check；远端规则与生产资格边界集中维护在 [发布准备](harness/docs/operations/release-readiness.md)。

## 数据与发布边界

- 不提交 `.env`、数据库、媒体文件、日志、原始测试产物或未加密备份。
- 长期备份与恢复必须同时覆盖内容事实库 SQLite 和媒体对象；只备份其中一项不能形成一致恢复点。`assistant_runtime` 及其 WAL/SHM 明确排除，Qdrant 丢失后由内容账本重建。
- `.run/`、`my_image/` 与 `my_blog_fork/` 是本地排除目录，不进入 Git 或 CI checkout。
- 在生产拓扑、持久化卷、TLS、安全环境变量、迁移和回滚演练全部完成前，项目保持 production **No-Go**。

## 文档入口

根 README 维护产品概览、三个代码目录、开发入口及发布边界；模块细节分别维护在 Web、API 与 Contracts README。功能、接口、启动模式或数据归属变化时同步对应入口；历史方案、实施过程和测试测量归入 `plan-build/`，正式规格与证据继续由 `harness/` 管理。

- [产品基线](harness/docs/product/brief.md)
- [架构边界](harness/docs/architecture/boundaries.md)
- [Web 应用边界](apps/web/README.md)
- [API 应用边界](apps/api/README.md)
- [共享契约边界](packages/contracts/README.md)
- [按主题归集的计划与报告](plan-build/README.md)
- [规格索引](harness/specs/INDEX.md)
- [发布准备](harness/docs/operations/release-readiness.md)
- [公开问答生产资格决策](harness/docs/decisions/20260830-public-qa-production-qualification.md)
- [Agent 工作入口](AGENTS.md)
