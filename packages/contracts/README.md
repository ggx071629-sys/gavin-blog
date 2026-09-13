---
id: contracts-boundary
level: L1
summary: Web 与 API 之间共享契约的边界
load_when:
  - contract-change
  - cross-stack-change
author: Gavin
---

# Contracts boundary

本目录保存 [FastAPI](../../apps/api/README.md) 与 [Web](../../apps/web/README.md) 之间的接口快照和派生类型，不是独立服务，也不存放业务实现或数据库。

## 文件与生成关系

| 文件 | 职责与来源 |
| --- | --- |
| [openapi.json](openapi.json) | 由 API 路由、参数与 Pydantic schema 导出的 OpenAPI 快照 |
| [api-types.d.ts](api-types.d.ts) | 由 openapi-typescript 从上述快照生成的 TypeScript 类型 |
| [generate.mjs](generate.mjs) | 依次调用 API 导出脚本和 TypeScript 生成器 |
| [package.json](package.json) | npm workspace `@gavin/contracts` 的生成命令与依赖 |

生成链路为 API 声明 → [scripts/export_openapi.py](../../apps/api/scripts/export_openapi.py) → OpenAPI → TypeScript。导出脚本显式使用 test Settings、内存数据库与 `_env_file=None`，不加载本机 `.env`。它描述已声明的接口，不能单独证明 Cookie、CSRF、所有错误分支或 SSE 事件的运行时行为。

## 更新与消费

从仓库根目录执行 `npm run contracts`。前提是根 npm 依赖已安装，`apps/api/.venv` 已按后端锁文件准备好；生成器使用 Windows 的 `Scripts/python.exe` 或 POSIX 的 `bin/python`。命令会重写两个派生文件，禁止手工维护其中的 schema。

Web 有两类消费者：

- [types/api.ts](../../apps/web/types/api.ts)：存量手写业务消费模型，接口变化时需显式同步。
- [types/account.ts](../../apps/web/types/account.ts) 与 [types/resume.ts](../../apps/web/types/resume.ts)：直接引用生成的 `components['schemas']`，账号与简历页面已接入。

字段或接口变化时，应同时更新 API 声明、生成两个派生物、检查手写类型和实际页面/parser，并运行受影响的契约及消费测试。纯 OpenAPI 元数据变化不要求修改无关消费模型。[release runner](../../scripts/run-release-check.mjs) 会重新生成并比较两个文件；发现过期时失败并保留生成结果供审查，不自动证明手写类型等价。

## 当前接口范围

公开助手增加 `PUT /assistant/turns/{turn_id}/feedback`，输入仅 value=helpful/unhelpful/null，输出 turn_id/value；会话恢复增加可空 feedback。管理 daily_activity 增加可空赞踩数量及 stages 数组；字段和生成类型按路由导出。反馈受原会话/CSRF/Origin及原回答TTL约束，不接受正文，也不调用模型。

以下简写路径统一以 `/api/v1` 为前缀，完整路径、方法、字段与枚举以 [openapi.json](openapi.json) 为准。

| 范围 | 当前能力 |
| --- | --- |
| 内容与发现 | 文章、项目、读书、栏目标签、公开搜索、上下文、wikilink 与反链 |
| 发布与管理 | 工作副本、显式发布、文章修订/差异/回滚、媒体生命周期、回收站和 Markdown 导入导出 |
| 公开资料 | Profile 及隐私字段、关于页工作副本/发布/修订、简历同步状态与刷新 |
| 账号 | 登录退出、固定账号信息、验证码改密/找回、登录会话查询和撤销 |
| 公开助手 | 可用性、短会话、SSE 提问、状态恢复与清除、当前有效简历附件 |
| 助手运营 | 状态概览、开放控制、总预算、同步任务、重试/重建/finalize、独立管理员试问与紧急停止 |

普通有界列表默认 20、最多 100 条，搜索最多 50 条，offset 最大 100000。管理员 `GET /admin/{articles,books,projects}/query` 返回 `items`、`total`、`counts{all,published,draft}`；关键词和状态筛选先于分页，counts 只应用关键词范围，total 同时应用状态。关键词是字面包含匹配，不把 SQL 通配符当模式。

## 账号合同

`/auth/account` 返回固定用户名、脱敏安全邮箱和邮件可用状态；改密使用当前密码、会话 CSRF 与用途绑定验证码。匿名恢复使用登录 CSRF，不接受用户输入邮箱或用户名。发码成功表示服务接受，不保证实际收件；改密/恢复成功撤销全部会话。

`/auth/sessions` 中的会话 ID 独立于 Cookie 及其哈希，时间为 UTC。认证响应 no-store；限流附 Retry-After，邮件不可用不回显供应商异常。前后端当前均已实现，边界见 [账号页面](../../apps/web/ACCOUNT-MANAGEMENT.md) 和 [API 账号说明](../../apps/api/README.md#账号管理后端)。

## 问答、预算与引用合同

匿名 `GET /assistant/availability` 只返回可用性，不创建会话或调用模型。session bootstrap、status、DELETE 与 questions SSE 使用既有 Cookie、CSRF 和幂等约束。questions 的畸形 JSON、严格类型、未知字段及问题/path 边界采用 `400 ErrorEnvelope`，该操作不声明默认 422；不能由此推断所有接口都没有 422。

会话视图包含 completed turns 和最多一个 active turn；`body_available=false` 时不再提供正文与引用。DELETE 204/202 分别表示本站清理完成/进行中，均不表示撤回供应商已收到的数据。SSE 与恢复的引用校验由 Web parser 执行，类型声明不能代替运行时校验。

管理概览只读取本地状态；不同数据库的 observed_at 不代表原子快照。试问会话和管理 CSRF 与匿名会话分离，试问引用可带有界 excerpt。总预算使用整数 micro-CNY 与 expected_version，受部署授权上限约束；保留分类账本与上限，不把总预算当成供应商账单保证。

索引来源包括 article、project、book、profile、about、resume；about 对应具备资格的当前发布修订，resume 对应当前有效简历版本。pending 只表示排队，不代表新版已可供问答使用。引用允许精确 `/about`（标题“关于 Gavin”）及 `/api/v1/assistant/resume/{32位小写hex版本ID}`，不接受任意外部 URL。

`GET /admin/profile/resume` 只读状态；`POST /admin/profile/resume/refresh` 需要 Session、CSRF 和 binding_epoch，202 表示入队、409 表示绑定冲突或未配置、429 表示冷却。首次/换址由保存 Profile 原子入队，同址替换需显式刷新。附件路由只返回当前有效版本 PDF，未知、暂停或撤销版本为 404，不跳到新版，不触发外部下载。

接口存在和类型生成成功均不等于已对访客开放或通过生产资格。历史实施与测试记录见 [plan-build](../../plan-build/README.md)，不把阶段性的“未实现”说明继续保留为当前合同。
