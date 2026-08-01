---
id: spec-20260801-profile-card
level: L1
summary: 首页首屏展示后台可配置的个人名片，支持公开读取与管理员版本化更新
load_when:
  - task:20260801-profile-card
author: Gavin
task_id: 20260801-profile-card
status: verified
---

# Profile card

## Context

首页首屏右侧的 "Current focus" 是静态写死的卡片，无法在后台维护。需要一张全站单例的个人名片，让访客快速了解 Gavin 的职业定位、简介、核心技能与公开联系方式；管理员可在 `/admin/profile` 编辑全部字段、控制城市与邮箱是否公开、实时预览，单次保存后首页立即生效。本任务只新增名片及其后台配置能力，不改动现有文章、项目、读书笔记、搜索与最近文章逻辑。

## Goal

访客在桌面端首页首屏右侧（移动端位于主介绍与最近文章之间）看到一张复用现有数字笔记卡片风格的名片；管理员登录后可在 `/admin/profile` 编辑资料、上传或选择头像、调整技能顺序、控制城市与邮箱公开状态并实时预览，保存后首页立即使用最新配置。

## Non-goals

- 多管理员或多份个人名片、草稿与单独发布流程、完整站点设置中心、博客品牌管理。
- 手机号、详细地址、身份证件、私人社交账号、站内联系表单、邮箱验证码。
- GitHub 数据自动同步、技能熟练度评分、简历在线编辑、PDF 简历上传与安全处理。
- 联系方式点击统计、精选文章或代表项目配置。
- 修改现有文章、项目、读书笔记、搜索或最近文章的数据获取与展示逻辑。

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

## Risks

- 邮箱字段需要格式校验，但不引入 `email-validator` 依赖：沿用 `validate_slug` 的正则 `field_validator` 风格，避免新增包。
- 公开响应必须按可见性裁剪字段：`ProfilePublic` 对城市/邮箱使用可选字段并在路由中按 `city_visible`/`email_visible` 条件赋值，配合 `response_model_exclude_none`，确保隐藏字段不出现在网络上。
- 单例一致性：迁移种入 `id=1` 默认行；路由始终操作 `id=1`，公开读取在行缺失时回退到内存默认值，满足 "首页不得空白报错"。
- 乐观锁与现有文章版本机制同构：冲突返回 `409` 并保留管理员输入，前端不静默覆盖。
- 头像与外链由现有媒体适配器产出 URL，名片不新增存储边界；头像加载失败由前端 `@error` 回退到字母标识。
- 预览复用 `ProfileCard` 但关闭实际跳转/复制，避免管理员编辑时误操作。
- 主题与触控：复用现有卡片边框、圆角、间距与按钮类；图标按钮触控目标尺寸沿用站点公共样式。

## Verification plan

- API：`tests/test_profile.py` 覆盖公开读取裁剪隐藏字段、管理员读取完整、更新需鉴权与 CSRF、非法 URL/邮箱/技能数量被拒、版本冲突返回 `409`、更新后版本递增、更新不影响文章数据；`tests/test_migrations.py` 覆盖新迁移建表与种入默认行。
- 契约：运行 `npm run contracts` 重新生成 `packages/contracts/openapi.json`，确认 `/profile` 与 `/admin/profile` 出现在快照中。
- Web 类型：`apps/web/types/api.ts` 增加 `ProfilePublic`、`Profile`（管理员）、`ProfileUpdate` 接口，`npm --workspace @gavin/web run typecheck` 通过。
- Web 单测：Vitest 覆盖技能校验/排序纯函数与公开响应裁剪逻辑（如有抽取）。
- Playwright：首页名片展示、隐藏字段不出现、GitHub 新标签打开、邮箱复制反馈、简历按钮、后台编辑保存后首页刷新生效、未保存离开提示。
- 回归：现有 Vitest、Nuxt typecheck、生产构建、`test_migrations` 与既有 API 测试全绿。
- Harness：`python -m tools.harness index` 注册新 spec，`python -m tools.harness verify 20260801-profile-card` 生成紧凑 evidence。

## Implementation record

- 新增 `Profile` 单例模型与 `20260801_0007` 迁移（种入 `id=1` 默认行）；公开 `GET /api/v1/profile` 按可见性从响应中移除城市/邮箱，管理 `GET/PATCH /api/v1/admin/profile` 要求 Session+CSRF、校验字段长度与 URL/邮箱格式，并以版本号乐观锁冲突返回 `409`。
- 首页首屏右侧渲染 `ProfileCard`（头像 `@error` 回退字母标识、邮箱复制 `aria-live` 反馈、GitHub/简历 `rel="noopener noreferrer"`）；`/admin/profile` 提供资料表单、技能增删排序、媒体选择头像与复用卡片的实时预览（关闭实际跳转），未保存修改时离开给予提示。
- 验证：`test_profile.py`、`test_migrations.py`（含默认行断言）、Vitest、typecheck、build、Profile E2E（含 `rel` 与未保存离开提示）、完整 E2E、Quality（WCAG axe + Lighthouse 四项 100）、`npm run contracts` 已重新生成含 `/profile` 与 `/admin/profile` 的 `openapi.json`。
- 2026-08-02 发布候选门禁再次通过 Profile API、迁移、Vitest、类型、构建、3 条 Profile E2E 与完整质量审计；spec 已具备关闭条件，等待原文进入首个 Git HEAD 后执行确定性归档。
