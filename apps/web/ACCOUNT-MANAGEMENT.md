# 写作台账号页面

本页描述当前账号 UI；应用边界见 [Web README](README.md)，后端接口和凭据生命周期见 [API 账号说明](../api/README.md#账号管理后端)。

`/admin/account` 位于运营导航，沿用 admin-core 和 Studio 双主题。展示服务端固定登录名、脱敏安全邮箱、改密及登录会话。安全邮箱与公开个人名片邮箱独立，页面不提供注册或换绑。

改密需当前密码和固定邮箱验证码；登录页“忘记密码”进入 `/admin/recover`，通过匿名 CSRF 发送和消费恢复码。新密码需 15–128 字符，提交前确认退出全部设备。成功清理表单并返回登录；密码、验证码和 challenge 不写浏览器持久存储。刷新会丢失本地 challenge，需要在服务端冷却后重新申请，不承诺跨刷新恢复表单。

发送成功文案只表示服务接受，不能证明实际收到。429 使用 Retry-After 秒数；错误验证码、403、422、邮件失败和会话失效分别反馈。服务器未配置邮件不影响普通登录，可按 [API 运维说明](../api/README.md#账号管理后端) 从终端恢复。

会话列表显示登录时间、最近活动与当前标记，UTC 时间转换为浏览器本地时区。单个、其他及当前会话退出均需确认；当前退出跳登录，失败不显示退出成功。撤销只影响后续认证，不回滚已执行的业务请求。

消费类型直接引用 `packages/contracts/api-types.d.ts` 的 AccountInfo、CodeIssued、SessionList 和 SessionItem，避免再次手抄模型。`account.spec.ts` 验证 UI 与真实会话；`account-flow.spec.ts` 用独立迁移数据库和实际 HTTP 验证密码闭环，邮箱 sender 使用本机测试收件文件，不能冒充真实邮件。真实邮件实投的历史结果见 [阶段四计划](../../plan-build/account-management/ACCOUNT-MANAGEMENT-PHASE-4.md)；它不保证当前邮箱配置或邮件送达状态。

维护入口：[账号页](pages/admin/account.vue)、[恢复页](pages/admin/recover.vue)、[消费类型](types/account.ts) 和 [账号反馈](utils/account.ts)。接口字段变化时重新生成 Contracts，并核对上述实际消费者；密码与会话规则改变时同步本页和 API 说明。
