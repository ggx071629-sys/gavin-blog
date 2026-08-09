---
id: spec-20260809-profile-contact-icons
level: L1
summary: 为个人名片接入独立网页地址并为联系方式提供一致的可访问 SVG 图标
load_when:
  - task:20260809-profile-contact-icons
author: Gavin
task_id: 20260809-profile-contact-icons
status: verified
---

# Context

公开个人名片当前以纯文字按钮展示 GitHub、复制邮箱和简历入口，缺少快速识别的图标；同时现有 Profile 模型没有独立的个人网页字段，只有 `github_url` 与 `resume_url`，无法准确承载用户要求的“网页”入口。

# Goal

为 Profile 增加可选 `website_url`，贯通 SQLite、FastAPI、OpenAPI、Web 类型、后台编辑与公开名片；在名片中为 GitHub、邮箱、个人网页和简历使用统一风格的内联 SVG 图标，并保留清晰文字标签。

# Non-goals

- 不引入第三方图标包或网络字体。
- 不把图标作为唯一可访问名称，也不改变邮箱复制交互。
- 不新增网页可见性开关；非空网页地址默认公开，与 GitHub、简历一致。
- 不修改页脚、关于页或项目卡片的链接设计。
- 不改变认证、CSRF、Session 或 Profile 乐观锁语义。

# Acceptance criteria

1. Alembic 新迁移为 `profiles` 增加可空、最大 500 字符的 `website_url`，支持 upgrade 与 downgrade。
2. Profile 的公开响应、管理响应与更新请求均包含可选 `website_url`；更新请求仅接受 HTTP(S) URL。
3. 后台个人名片表单提供“个人网页”输入，保存后实时预览与公开首页一致。
4. 公开名片在字段存在时展示 GitHub、复制邮箱和个人网页入口，分别使用 GitHub、信封和地球线性 SVG；简历入口使用下载 SVG。
5. 所有 SVG 标记为装饰性 `aria-hidden`，按钮或链接保留文字标签和现有可访问名称；GitHub、网页和简历新标签打开并带安全 `rel`。
6. 字段为空时对应入口不渲染；隐藏邮箱仍不会进入公开响应或公开名片。
7. OpenAPI 快照、Web 类型、API/Profile 测试和 Profile E2E 与新字段保持同步。

# Risks

- 数据迁移或契约遗漏会导致旧数据库启动失败或前后端字段漂移。
- 仅增加图标而移除标签会降低可访问性；实现必须采用“图标 + 文字”。
- 新增一行联系方式可能拉高移动端名片，但不得造成横向溢出或缩小点击目标。
- GitHub 品牌图标与通用线性图标视觉重量不同，需要统一 20px 画布和 `currentColor`。

# Verification plan

- 先扩展 API Profile 测试和 Profile E2E，使新字段与图标断言在实现前失败。
- 运行 Alembic upgrade/downgrade/upgrade 验证迁移链。
- 运行 API Profile 测试、Web 单测、类型检查、Profile E2E 和生产构建。
- 重新生成并验证 OpenAPI 契约快照。
- 运行首页质量场景检查双主题、双视口的 axe 与横向溢出，并检查生成截图。
- 运行 `python -m tools.harness verify 20260809-profile-contact-icons`。
