---
id: spec-20260910-account-management
level: L1
summary: 单管理员持久凭据、邮件恢复和写作台会话管理
load_when:
  - task:20260910-account-management
task_id: 20260910-account-management
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - ACCOUNT-MANAGEMENT-DESIGN.md
  - apps/api/README.md
  - packages/contracts/README.md
  - harness/docs/decisions/20260910-account-management.md
  - apps/web/ACCOUNT-MANAGEMENT.md
documentation_reason: 固化凭据初始化、邮件配置、终端恢复及跨端契约并登记验收结果。
state_history:
---
# Context
用户按四阶段主计划授权设计、实施与验收。原进程内密码已在阶段二改为持久凭据；本轮继续 Web 消费及联调。已有写作台 UI 和无关工作区改动必须保留。
# Goal
本次按最新指令继续第三阶段页面与第四阶段验收。本机邮件配置已填写且用户已授权真实验收发信；A4-02 的真实 SMTP 接受、实际收取和验证码闭环未全部完成前不关闭。不以替身或隔离验证替代真实投递。
按根目录 ACCOUNT-MANAGEMENT-DESIGN.md 六章契约提供固定单管理员账号、持久密码、邮件验证改密/恢复及会话管理。
# Non-goals
不新增注册、多用户、换绑邮箱、日常登录验证码；不部署、不修改真实日常凭据、不把邮件替身当实投证据。
# Acceptance criteria
- AC-1: 旧库迁移后可登录；新密码跨重启有效，配置不覆盖，终端无邮件恢复清除全部会话。
- AC-2: 验证码用途、过期、错误限次、重发限额、邮件失败、并发消费与改密全会话失效符合设计。
- AC-3: 会话时间、当前标记、单个及其他撤销真实；并发旧凭据登录不能绕过失效。
- AC-4: 现有登录 CSRF、限流、写作鉴权和运行配置保持兼容，账户响应禁止缓存与秘密泄漏。
- AC-5: OpenAPI 与派生类型及 Web 消费同步，TLS 邮件边界与配置/终端恢复说明可执行。
- AC-6: 账号页、登录恢复及会话管理复用现有写作台，错误/忙碌/确认/认证失效真实，双主题窄屏与键盘可用，隔离 Web/API 改密恢复撤销闭环通过。
# Risks
SMTP 投递与数据库无分布式事务，使用 pending/active 和版本复检；账号限额可能被匿名耗尽，保留终端恢复。真实邮件配置与实投授权尚需在 A4-02 核实，不能提前关闭 spec。只提交本任务文件，保留无关修改。
# Verification plan
## Verification cases
- AC-1 => M06-ACCOUNT-CREDENTIAL-01, M06-ACCOUNT-CLI-01, M06-UNIT-MIGRATIONS-01
- AC-2 => M06-ACCOUNT-CODE-01, M06-ACCOUNT-PASSWORD-01
- AC-3 => M06-ACCOUNT-SESSION-01
- AC-4 => M06-ACCOUNT-COMPAT-01, M06-P0-01, M06-UNIT-RUNTIME-SAFETY-01, M06-UNIT-ENVIRONMENT-ISOLATION-01
- AC-5 => M06-ACCOUNT-CONTRACT-01
- AC-6 => M06-ACCOUNT-UI-01, M06-ACCOUNT-FLOW-01, M06-ACCOUNT-FEEDBACK-01, M06-UNIT-ADMIN-01
## Gates
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5
- e2e => AC-6
- web-quality => AC-6
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6


