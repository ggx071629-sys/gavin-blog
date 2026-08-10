---
id: spec-20260809-runtime-security-boundaries
level: L1
summary: 统一运行时配置校验并加固浏览器响应头与媒体预解码边界
load_when:
  - task:20260809-runtime-security-boundaries
author: Codex
task_id: 20260809-runtime-security-boundaries
status: active
---

# Context

项目审计确认三项发布前安全缺口：Worker 绕过 API 和迁移使用的运行时校验且遗漏检索模型 root/backend；Nuxt HTML 缺少应用层浏览器安全响应头；媒体上传在像素上限和实际格式检查前执行 EXIF 转置与完整解码。批次 4 只处理 AUD-05、AUD-07、AUD-10，不提前创建或实现后续批次。

# Goal

建立所有生产入口一致的 fail-closed 配置边界，让 Worker 使用与 API 相同的检索配置；为正常、错误和后台 HTML 提供可验证的安全响应头；在任何图像转置或完整像素解码前拒绝不允许的格式、超出产品像素上限的图片和 Pillow 解压炸弹告警。

# Non-goals

- 不在本批次启用强制 CSP；先上线 Report-Only，待 AUD-16 字体自托管及来源收敛完成后再强制。
- 不选择或实现公网部署平台、TLS 终止层、容器编排或外部 CSP 报告服务。
- 不修改 LLM、检索模型、网页抓取 allowlist 或媒体格式的业务能力。
- 不处理 AUD-08/09/11/13～20，也不预建后续 active spec。

# Acceptance criteria

1. 提供单一运行时 Settings 构建入口，API、Worker、Alembic 迁移及依赖默认配置的诊断路径共享同一 `validate_runtime()`；显式注入的测试 Settings 仍保持可控。
2. production 环境在非空 `GAVIN_URL_FETCH_ALLOWLIST` 或 `GAVIN_RETRIEVAL_MODEL_BACKEND=double` 时，在进入服务循环或数据库任务前立即失败；development/test 环境仍允许受控替身。
3. `run_worker.py` 显式传递 `retrieval_model_root`、`retrieval_model_backend`，启动日志只包含 environment、模型 backend/root 等非敏感摘要，不输出密码、API key 或完整数据库 URL；真实 CLI `--once` 测试覆盖成功启动与生产拒绝。
4. Nuxt 服务端在 200、404、5xx 以及登录/后台 HTML 上设置 `Content-Security-Policy-Report-Only`，且策略至少包含 `frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`、`form-action 'self'`；同时强制设置 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、明确 Referrer-Policy 和最小 Permissions-Policy。
5. 应用不为本地 HTTP 响应伪造 HSTS；发布文档明确 HSTS 由 HTTPS 边缘层负责，并要求在最终公网响应上验证。
6. 媒体上传保留字节上限，并在 `ImageOps.exif_transpose()`、`load()` 或其他完整像素解码前检查文件实际 format 和原始宽高乘积；超限返回 422。
7. 请求局部将 `Image.DecompressionBombWarning` 转为可控 422，继续捕获 `DecompressionBombError`，且不修改 Pillow 进程级全局阈值。
8. 小压缩体积但超大尺寸的有效图片测试证明拒绝发生在转置/解码前；不受支持格式也在转置/解码前拒绝。

# Risks

- Nuxt/Nitro 错误响应可能绕过页面级中间件；必须以真实 404 和故障注入 5xx 响应验证，而非只测试常量。
- Report-Only 不阻止违规资源，仅提供上线前观测；若误称为强制 CSP 会制造虚假安全感。
- Worker fail-closed 可能暴露已有生产环境中的测试 backend 或抓取 allowlist 配置；这是预期启动失败，需给出明确但不泄密的错误。
- Pillow `Image.open()` 是惰性的，但插件仍会解析文件头；产品像素上限必须在任何会触发完整像素分配的操作前检查，并保留进程/容器内存限制作为部署纵深。

# Verification plan

1. API 单测覆盖统一 settings 工厂、production allowlist/double 拒绝、test/development 允许和既有密码/Cookie/CORS 约束。
2. Worker 入口测试使用真实 CLI `--once` 证明安全配置可启动、非法 production 在数据库工作前退出；另以构造替身断言模型 root/backend 参数完整传入。
3. 媒体 API 测试用有效但超产品像素上限的压缩图片和不允许格式证明 transpose/load 未执行，并覆盖 `DecompressionBombWarning` 的请求级 422。
4. Web 生产构建/预览门禁对公开页、404、故障注入 5xx、登录与后台页断言安全头；保留现有功能和无障碍检查。
5. 运行 API lint/test、Web typecheck/unit/build、相关 Playwright quality/failure suites，再完整执行 `npm run quality:release`。
6. 从 `harness/` 运行 `python -m tools.harness verify 20260809-runtime-security-boundaries`；全部验收通过后使用确定性 close 命令关闭 spec。
