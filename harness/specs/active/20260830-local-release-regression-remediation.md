---
id: spec-20260830-local-release-regression-remediation
level: L1
summary: 修复内容写 fence 并发回归、质量门禁收尾与服务端构建目标漂移，恢复可重复的本地发布候选
load_when:
  - task:20260830-local-release-regression-remediation
author: Gavin
task_id: 20260830-local-release-regression-remediation
status: active
verification_profile: release
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
documentation_reason: 本任务修正项目状态和内容写 fence 的运行语义，必须同步公开项目状态与 API 持久化边界。
state_history:
---

# Context

生产资格任务因当前仍处于功能开发阶段而保持 frozen，且不得访问真实服务器、域名或供应商。本地 `npm run quality:release` 在同一 API owner 内并发创建文章、项目和读书笔记时只允许第一个请求取得非阻塞跨进程文件锁，其余正常请求错误返回 `503 content writes are temporarily fenced`；质量矩阵因此失败，并在失败后长时间未退出。相同构建还报告 Nitro `es2019` 目标无法安全表达可信代理 CIDR 实现使用的 BigInt。根 README 仍把已经压缩归档的 Admin Login 规格写成当前保留任务。

# Goal

恢复一份不依赖任何真实部署的可重复本地发布候选：单 API owner 内的正常并发内容 mutation 必须有界串行且保持既有成功合同，外部备份／恢复 fence 仍立即 fail closed；质量门禁无论通过或失败都能在有界时间内回收本地服务进程；Nitro 服务端构建目标与受支持的 Node 22／BigInt 能力一致；项目状态文档与权威 Spec 索引一致；最终完整 release gate 从干净工作树通过并正常退出。

# Non-goals

- 不恢复或改写 `20260830-public-qa-production-qualification`，不生成生产 profile、部署资产或资格 manifest。
- 不访问真实服务器、域名、CDN、Qdrant 或 Chat／Embedding 供应商，不开启 Web launcher、API capability 或 runtime gate。
- 不通过删除并发测试、把并发 fixture 改为串行、放宽 201 断言或吞掉 503 来制造绿灯。
- 不让普通请求无限等待外部备份／恢复 fence，也不削弱备份一致性或单 API owner 边界。
- 不把远端 push、PR、CI 或合并结果冒充本地产品验证；远端集成只在本任务本地关闭后单独执行和报告。

# Acceptance criteria

- AC-1: 应用为每个 API 实例建立进程内 async 内容写序列化边界；同一实例中的并发认证内容 mutation 在没有外部 fence 时均按原合同成功，不因彼此竞争跨进程文件锁返回 503。序列化后每个请求仍单独取得并释放既有跨进程 fence；外部备份／恢复进程持锁时 mutation 继续立即返回稳定 503、`Retry-After: 5` 且不写入数据库。取消、异常和响应完成路径不得遗留进程内或文件锁。
- AC-2: Web 质量门禁保留并发 fixture 和原始断言；无论质量场景通过还是产生受控失败，Playwright、Nuxt preview、隔离 API 和浏览器子进程都在有界时间内退出。release runner 对子 gate 设定与 Harness 注册门槛一致的超时，并在 Windows 上清理整棵子进程树；超时必须非零并报告对应 stage，不能继续后续 gate或留下占用端口的孤儿。
- AC-3: Nitro 服务端构建明确使用支持 BigInt 的目标并与项目声明的 Node 22 运行基线一致；可信代理 IPv4、IPv4-mapped IPv6、IPv6 和 CIDR 单元测试保持通过，生产构建不再输出 `Big integer literals are not available in ... es2019` 警告。
- AC-4: 根 README 不再把已压缩的 Admin Login 规格描述为当前 active；API README 准确记录普通单 owner mutation 的进程内序列化与外部备份 fence fail-closed 区别。历史已取消、退役或压缩任务不被重新列为待完成。
- AC-5: 当前 HEAD 的 API lint／测试、Harness tests、OpenAPI 一致性、Web 类型／单测／构建／质量／失败态、核心 E2E 与 Harness integrity 均由一次完整 `npm run quality:release` 成功覆盖；命令正常退出、工作树保持干净，local-only change coverage skip 只作为明确记录而不被描述成远端 CI 证据。

# Risks

- 仅把文件锁改成阻塞锁可能卡住事件循环或让外部备份造成无限等待；进程内 async 序列化和跨进程非阻塞 fence 必须分层。
- 在响应流仍未结束时提前释放 fence 会破坏未来 mutation 路由；在取消路径未释放则会永久阻塞单 owner。中间件边界必须由并发和异常测试证明。
- Windows 只终止 npm／shell 父进程会遗留 Python、Nuxt 或 Chromium；监督必须针对进程树，并验证端口与子进程回收，而不依赖人工 Ctrl+C。
- 单纯忽略 esbuild 警告会保留配置漂移；提高服务端目标必须与 Node 22 最低版本一致，不能无意改变浏览器兼容目标。
- 本地 release 通过不能证明远端 CI、分支保护、生产部署或公开问答资格。

# Verification plan

- api-lint => AC-1
- api-tests => AC-1
- web-quality => AC-2, AC-3, AC-4
- harness-integrity => AC-4
- release => AC-1, AC-2, AC-3, AC-4, AC-5
