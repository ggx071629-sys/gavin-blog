---
id: archive-20260809-runtime-security-boundaries
level: L2
summary: 统一运行时配置校验并加固浏览器响应头与媒体预解码边界
load_when:
  - task:20260809-runtime-security-boundaries
author: Codex
task_id: 20260809-runtime-security-boundaries
status: compressed
restoration_source: "1e5479d6b07db4344f7f90a7dfc669cf94afb001:harness/specs/active/20260809-runtime-security-boundaries.md"
restored_at: 2026-08-11
---

# 20260809-runtime-security-boundaries

Deterministic compressed record. The original active spec remains in Git history.

## Goal

建立所有生产入口一致的 fail-closed 配置边界，让 Worker 使用与 API 相同的检索配置；为正常、错误和后台 HTML 提供可验证的安全响应头；在任何图像转置或完整像素解码前拒绝不允许的格式、超出产品像素上限的图片和 Pillow 解压炸弹告警。

## Acceptance criteria

1. 提供单一运行时 Settings 构建入口，API、Worker、Alembic 迁移及依赖默认配置的诊断路径共享同一 `validate_runtime()`；显式注入的测试 Settings 仍保持可控。
2. production 环境在非空 `GAVIN_URL_FETCH_ALLOWLIST` 或 `GAVIN_RETRIEVAL_MODEL_BACKEND=double` 时，在进入服务循环或数据库任务前立即失败；development/test 环境仍允许受控替身。
3. `run_worker.py` 显式传递 `retrieval_model_root`、`retrieval_model_backend`，启动日志只包含 environment、模型 backend/root 等非敏感摘要，不输出密码、API key 或完整数据库 URL；真实 CLI `--once` 测试覆盖成功启动与生产拒绝。
4. Nuxt 服务端在 200、404、5xx 以及登录/后台 HTML 上设置 `Content-Security-Policy-Report-Only`，且策略至少包含 `frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`、`form-action 'self'`；同时强制设置 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、明确 Referrer-Policy 和最小 Permissions-Policy。
5. 应用不为本地 HTTP 响应伪造 HSTS；发布文档明确 HSTS 由 HTTPS 边缘层负责，并要求在最终公网响应上验证。
6. 媒体上传保留字节上限，并在 `ImageOps.exif_transpose()`、`load()` 或其他完整像素解码前检查文件实际 format 和原始宽高乘积；超限返回 422。
7. 请求局部将 `Image.DecompressionBombWarning` 转为可控 422，继续捕获 `DecompressionBombError`，且不修改 Pillow 进程级全局阈值。
8. 小压缩体积但超大尺寸的有效图片测试证明拒绝发生在转置/解码前；不受支持格式也在转置/解码前拒绝。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-runtime-security-boundaries.json](../../verification/evidence/20260809-runtime-security-boundaries.json)

Closed at 2026-08-10T13:15:12.421245+00:00.
