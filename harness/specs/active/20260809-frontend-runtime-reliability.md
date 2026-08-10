---
id: spec-20260809-frontend-runtime-reliability
level: L1
summary: 消除 SSR 共享状态漂移并统一轮询、媒体逐项反馈与 Profile 初态
load_when:
  - task:20260809-frontend-runtime-reliability
author: Codex
task_id: 20260809-frontend-runtime-reliability
status: active
---

# Context

审计批次 5 覆盖 AUD-08、AUD-09、AUD-11、AUD-15：公开 Profile 的同一 AsyncData key 使用不同 handler 导致 `NUXT_E3004`，主题图标依赖服务端未知的 system color mode 导致水合不一致；多类孵化详情页各自用 async `setInterval` 轮询；多文件媒体上传把逐项事务伪装为整体结果；fresh database 的空技能 Profile 又被更新 schema 与页面校验拒绝。

# Goal

让生产 SSR 与共享数据处理无警告，使孵化轮询具备单飞、可见性、终态、退避和卸载取消边界；让媒体上传准确展示每个文件的成功或失败并及时刷新成功资产；允许合法的零技能 Profile 修改其他字段。

# Non-goals

- 不处理移动抽屉、触控目标和字体自托管（批次 6）。
- 不改变媒体服务端逐文件事务为批量原子事务，也不引入新上传 API。
- 不改变 Profile 技能最大数量、单项长度或公开空列表展示语义。
- 不修改孵化任务状态机、轮询 API 响应契约或后台作业调度。
- 不预建后续 active spec。

# Acceptance criteria

1. 公开 Profile 读取集中到唯一 composable；共享 AsyncData key 的 handler 与关键 options 完全一致，首页、默认布局及其他消费者不再自行定义同 key handler。
2. 依赖 system color mode 的公开与后台主题图标使用 SSR 稳定 DOM/CSS 或显式 unknown 占位；生产首页及主题切换不产生 hydration mismatch、Vue error 或 `NUXT_E3004`。
3. E2E 监听 console/pageerror，并把 hydration mismatch、Vue error、`NUXT_E3004` 与未处理错误作为失败，而非只把日志留在 WebServer 输出。
4. 所有需要持续刷新的孵化详情页使用 `useIncubatorPolling`，不保留页面私有 async `setInterval`。
5. 统一轮询在一次请求完成后才用 `setTimeout` 安排下一次，间隔下限 2000ms；同一实例最多一个 in-flight 请求，hidden 暂停、visible 恢复，终态停止，卸载后中止/忽略在途结果；失败指数退避并暴露重试状态与最后成功时间供页面展示。
6. 多文件媒体上传逐文件继续执行，展示每个文件的 pending/success/error 结果；任一成功后刷新资产列表，后续失败不抹掉成功事实，失败项可明确重试且不会自动重传成功项。
7. API 与 Web 允许 Profile `skills=[]`，仍拒绝空白技能、超过 6 项或单项超长；fresh database 首次只修改简介、头像或其他非技能字段可成功保存。

# Risks

- 轮询 API 改造涉及多个页面，若终态判断遗漏会造成停止过早或后台请求泄漏；必须逐页保留原终态条件。
- AbortSignal 只能在 refresh 支持时真正取消网络；不支持的调用至少必须单飞并在卸载后忽略结果，不能伪称已取消。
- console 门禁会立即暴露已有真实警告；只允许修复根因，不得通过过滤所有 console 输出使门禁失真。
- 媒体逐项继续执行会延长含失败批次的总耗时，但准确结果优先于虚假的整体失败。

# Verification plan

1. Vitest 覆盖统一 Profile composable 静态契约、SSR 稳定主题 DOM、慢请求单飞、hidden/visible、终态、退避、卸载以及零技能校验。
2. MediaUploader 组件测试注入“成功/失败/成功”，断言三项状态、成功资产刷新和只重试失败项。
3. API Profile 测试在 fresh database 以 `skills=[]` 修改非技能字段成功，并保留技能边界反例。
4. 将生产 quality E2E 的 console/pageerror 监听设为强约束，运行首页深浅主题与后台相关页面。
5. 运行 API lint/test、Web typecheck/unit/build、相关 Playwright 套件及完整 `npm run quality:release`。
6. 从 `harness/` 运行 verify；全部通过后用确定性 close 命令归档本 spec。
