---
id: archive-20260809-electric-editorial-incubator-workbench
level: L2
summary: 将知识孵化全链路迁移到 Electric Editorial 双主题高密度工作台并保留全部业务契约
load_when:
  - task:20260809-electric-editorial-incubator-workbench
author: Gavin
task_id: 20260809-electric-editorial-incubator-workbench
status: compressed
restoration_source: "c3da86edaddec06b596dabaaad239f61d5e36319:harness/specs/active/20260809-electric-editorial-incubator-workbench.md"
restored_at: 2026-08-11
---

# 20260809-electric-editorial-incubator-workbench

Deterministic compressed record. The original active spec remains in Git history.

## Goal

在不改变 API 契约、数据库模型、公开／后台 URL、认证规则、知识孵化状态机、轮询语义、外发确认和发布原子性的前提下，将 12 个知识孵化路由迁移到 Electric Editorial 双主题高密度后台体系，形成移动可用、证据可扫描、操作可回溯并满足 WCAG AA 的完整孵化工作台。

## Acceptance criteria

- 12 个知识孵化路由全部使用 admin-core，或使用建立在 admin-core 之上的无业务耦合孵化工作台组合；旧 admin 布局不再承载这些路由。主导航仅保留一个“知识孵化”入口，桌面侧栏与移动抽屉的当前项、跳到正文、焦点和退出行为保持正确。
- IncubatorShell 重构为孵化上下文壳层：保留概览／待处理／审计报告／孵化草稿／任务五入口、服务端 attention 数量、aria-current 与面包屑；窄屏下二级导航可扫描、可键盘到达且不挤压主内容。
- 详情页的 IncubatorChainNav 保留来源→审计计划／报告→草稿计划／草稿→发布计划→文章修订的真实上一步／下一步关系。链条状态必须来自真实数据，不显示尚不存在或不可到达的步骤，不能只靠颜色表达当前与完成状态。
- 概览页按“立即处理→摄入→池状态→系统健康与任务→最近批次”的操作优先级组织真实信息；混合 Markdown／TXT 与 URL 提交、限制说明、逐项结果、重复／不支持反馈、部分成功重试、attention、能力健康、索引重建、任务摘要、Token 消费和最近批次行为全部保留。
- 待处理池保留 status／source_type／q 的稳定 URL 查询、有界分页、刷新／前进／后退／复制链接一致性、选择随查询／换页／刷新收敛、仅 inbox 可选和审计计划入口。移动端筛选区按主要条件优先折叠，已应用条件始终可见且可清除。
- 待处理详情保留原始内容纯文本安全预览、标准化 Markdown、标题／正文修订、基础修订号乐观锁、409 冲突、修订历史、任务历史、全文／降级检索预览、丢弃、恢复、失败重试和永久删除确认。任何原始 HTML 不得注入 DOM。
- 审计计划保留逐项本地规划状态、来源数量、Token 估算、外发范围、明确的 external_transfer_confirmed 确认和逐项确认结果；计划未 ready 时不能提前确认，失败、过期和部分结果必须有文本语义。
- 审计池保留 status／role／confidence／source_type／degraded／日期／关键词筛选、URL 同步、有界分页、选择收敛、批量确认和批量丢弃。状态、置信、降级和冲突使用一致的状态语言并附文字／图标，不只使用色块。
- 审计详情把“结论与可执行操作”置于前部，把证据片段、候选旧文快照、模型调用、Token 明细与人工决定组织为可扫描区域；AI 原判和当前有效判定必须明确区分。人工改判、目标文章、确认、丢弃、冲突裁决、反馈重跑与创建草稿计划的资格和请求保持原样。
- 草稿池保留 role／status／日期／关键词筛选、URL 同步、有界分页、选择收敛和仅对就绪草稿创建批量发布计划的资格检查；已发布、发布失败、冲突来源与角色均有非颜色状态说明。
- 草稿计划保留外发范围、模型、签发锚点、分类候选、Token 估算、external_transfer_confirmed 确认和规划轮询；确认层具备 dialog 语义、可读标题、焦点进入／约束／返回、Esc 和明确取消。
- 草稿详情保留 supplement／rewrite／new_branch 三类真实编辑结构、AutosaveQueue、版本冲突、未保存／保存中／已保存／错误状态、角色预览、发布准备度、slug 冲突、版本激活、版本 diff、Token 账本、反馈重生成、丢弃和创建发布计划。发布相关操作前必须 flush 待保存内容或按既有失败语义阻断。
- 发布计划保留 blocked／stale／ready 等资格、逐项角色、风险、阻断码、差异、引用公开性、执行记录和最终 publish_confirmed 确认；逐项发布保持既有原子语义，成功、失败、部分失败及目标文章／修订链接全部可追溯。
- 任务列表保留 status／job_type／owner_type／日期筛选、URL 同步、有界分页、全部任务类型、真实阶段、错误码／错误消息和安全取消；任务详情保留归属、阶段、资源链接、LLM_OUTCOME_UNKNOWN 告警和终态。取消请求不能被视觉状态误报为已取消。
- 轮询继续遵守现有终态集合、周期和可见性策略；刷新导致的数量、状态和时间变化不得抢夺焦点、重置用户输入或造成屏幕阅读器播报风暴。仅对操作结果和关键终态变化使用克制的 aria-live。
- 浅色和深色是分别调校的界面：背景层、边框、阴影、文本层级、状态面和交互态都使用语义令牌。酸性绿不用于未达到 4.5:1 的小号文字；状态与正文达到 WCAG AA，焦点达到可见性要求。
- 桌面端维持高密度双栏／主从布局；390×844 下重排为单列，筛选、批量操作、长标题、原文、Markdown、diff、Token 和任务错误均不造成页面级横向溢出。表格或代码区域只允许组件内部受控滚动。
- 所有核心操作可键盘完成；视觉顺序与焦点顺序一致；输入具备可见标签和就近错误；触控目标至少 44×44px，相邻目标至少 8px；动画仅用于 1–2 个关键反馈并尊重 prefers-reduced-motion。
- 保留现有 data-testid 及 ingestion、retrieval、workbench、LLM audit、draft、publishing 高价值闭环。为修复脆弱选择器可新增稳定语义或 testid，但不得通过删除断言、跳过用例或降低规则来获得通过。
- 12 个路由执行 light/dark × 1440×1100/390×844 的四象限视觉与无溢出检查，共 48 个基础视图；另覆盖 loading、empty、partial success、failed、conflict、stale、running、cancellation requested、cancelled 等代表动态状态。截图与重型报告只留本地。
- 每个页面族至少一个固定数据代表状态执行 axe WCAG 2.0／2.1 A/AA，自动扫描零违规；对话框、批量操作栏、轮询终态、错误反馈和移动导航执行人工键盘／屏幕阅读器语义检查。
- Nuxt 类型检查、全部 Vitest、生产构建、适用 Playwright、质量门禁、git diff --check 和 Harness 验证通过；公开首页 Lighthouse 四项继续不低于 90，所有管理页维持 noindex,nofollow。
- 实现 diff 不得包含 my_blog_fork/、两个冻结 spec、apps/api/、packages/contracts/ 或数据库迁移；若发现完成 UI 必须改变这些边界，停止实现并单独升级 spec，不得在本阶段偷渡。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-electric-editorial-incubator-workbench.json](../../verification/evidence/20260809-electric-editorial-incubator-workbench.json)

Closed at 2026-08-09T11:32:25.282277+00:00.
