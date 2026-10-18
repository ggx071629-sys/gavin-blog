---
id: archive-20260910-account-management
level: L2
summary: 单管理员持久凭据、邮件恢复和写作台会话管理
load_when:
  - task:20260910-account-management
task_id: 20260910-account-management
status: compressed
documentation_impact: required
documentation_targets:
  - ACCOUNT-MANAGEMENT-DESIGN.md
  - apps/api/README.md
  - packages/contracts/README.md
  - harness/docs/decisions/20260910-account-management.md
  - apps/web/ACCOUNT-MANAGEMENT.md
documentation_reason: 固化凭据初始化、邮件配置、终端恢复及跨端契约并登记验收结果。
evidence_sha256: a56401c84cd5827c2acd0e31425fd4c70c6e878bdf1235190cdfe9f8cba955f8
state_history:
---

# 20260910-account-management

Deterministic compressed record. The original active spec remains in Git history.

## Goal

本次按最新指令继续第三阶段页面与第四阶段验收。本机邮件配置已填写且用户已授权真实验收发信；A4-02 的真实 SMTP 接受、实际收取和验证码闭环未全部完成前不关闭。不以替身或隔离验证替代真实投递。
按根目录 ACCOUNT-MANAGEMENT-DESIGN.md 六章契约提供固定单管理员账号、持久密码、邮件验证改密/恢复及会话管理。

## Acceptance criteria

- AC-1: 旧库迁移后可登录；新密码跨重启有效，配置不覆盖，终端无邮件恢复清除全部会话。
- AC-2: 验证码用途、过期、错误限次、重发限额、邮件失败、并发消费与改密全会话失效符合设计。
- AC-3: 会话时间、当前标记、单个及其他撤销真实；并发旧凭据登录不能绕过失效。
- AC-4: 现有登录 CSRF、限流、写作鉴权和运行配置保持兼容，账户响应禁止缓存与秘密泄漏。
- AC-5: OpenAPI 与派生类型及 Web 消费同步，TLS 邮件边界与配置/终端恢复说明可执行。
- AC-6: 账号页、登录恢复及会话管理复用现有写作台，错误/忙碌/确认/认证失效真实，双主题窄屏与键盘可用，隔离 Web/API 改密恢复撤销闭环通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260910-account-management.json](../../verification/evidence/20260910-account-management.json)

SHA-256: `a56401c84cd5827c2acd0e31425fd4c70c6e878bdf1235190cdfe9f8cba955f8`

Closed at 2026-09-10T16:34:46.168813+00:00.
