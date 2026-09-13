---
id: archive-20260801-profile-card
level: L2
summary: 首页首屏展示后台可配置的个人名片，支持公开读取与管理员版本化更新
load_when:
  - task:20260801-profile-card
author: Gavin
task_id: 20260801-profile-card
status: compressed
---

# 20260801-profile-card

Deterministic compressed record. The original active spec remains in Git history.

## Goal

访客在桌面端首页首屏右侧（移动端位于主介绍与最近文章之间）看到一张复用现有数字笔记卡片风格的名片；管理员登录后可在 `/admin/profile` 编辑资料、上传或选择头像、调整技能顺序、控制城市与邮箱公开状态并实时预览，保存后首页立即使用最新配置。

## Acceptance criteria

- 管理后台导航存在 "个人名片" 入口，指向 `/admin/profile`，未登录用户不可访问该页面与管理接口。
- 公开接口 `GET /api/v1/profile` 只返回允许公开的字段；被关闭显示的城市和邮箱从响应中直接移除，而非置空。
- 管理员接口 `GET /api/v1/admin/profile` 返回完整配置与当前版本号；`PATCH /api/v1/admin/profile` 要求管理员 Session 与 CSRF，校验全部字段长度与格式，使用版本号乐观锁，冲突时返回 `409`。
- 必填字段：公开名称（≤80）、职业定位（≤120）、个人简介（≤240）；核心技能 1～6 个、每项 ≤30。
- 可选字段：头像 URL、城市（≤80）、GitHub 地址（HTTP(S)）、公开邮箱（合法邮箱）、简历地址（HTTP(S)）、显示城市、显示邮箱。未配置或未公开时相关元素完全隐藏，不留空白占位。
- 首页桌面端名片位于首屏右侧、替换原 "Current focus"；移动端名片位于主介绍与最近文章之间，不影响其他内容顺序。
- GitHub 仅图标，新标签页打开（`rel="noopener noreferrer"`），悬停提示 "GitHub"，键盘可操作，有可感知无障碍名称。
- 邮箱仅图标，点击复制完整地址、不打开邮件客户端；成功后图标短暂变勾号并有 "已复制" 反馈，约 2 秒恢复；失败时显示邮箱原文并提示手动复制；复制结果通过 `aria-live` 区域通知屏幕阅读器。
- "查看简历" 为带文字次级按钮，新标签页打开；未配置时不显示。
- 未设置头像时显示 Gavin 字母标识；头像加载失败自动回退到默认标识，不显示破损图标。
- 后台 `/admin/profile` 提供资料编辑表单与实时预览，桌面左右、移动上下；预览复用首页 `ProfileCard` 组件，预览内 GitHub/邮箱/简历跳转与复制可关闭。
- 技能可添加、删除、排序，最多 6 个；统一 "保存设置" 按钮一次提交全部修改；保存成功提示 "个人名片已更新"；存在未保存修改时离开页面给予提示；保存失败保留输入并显示错误。
- 数据库使用单例个人资料表（明确字段，非键值对），含版本号与时间戳；首次迁移种入默认行，保证首页永不空白报错。
- 非法 GitHub、邮箱或简历地址不能保存；并发修改不会静默覆盖较新配置。
- 深色、浅色、桌面与移动布局均正常；鼠标、键盘与触屏均可完成操作；图标按钮有无障碍名称与清晰聚焦态；文本与按钮颜色满足 WCAG AA。
- 现有首页文章、文章详情、项目、读书、搜索与其他业务功能不受影响。
- Harness、API 测试、Web 测试、类型检查、生产构建与适用的 Playwright 旅程全部通过。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-profile-card.json](../../verification/evidence/20260801-profile-card.json)

Closed at 2026-08-01T16:43:27.586778+00:00.
