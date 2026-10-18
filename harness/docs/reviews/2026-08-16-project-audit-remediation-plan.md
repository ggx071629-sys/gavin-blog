---
id: review-2026-08-16-project-audit-remediation-plan
level: L2
summary: 已闭环的 2026-08-16 项目审计历史修复计划
load_when:
  - historical-audit
  - audit:2026-08-16
author: Grok
---

# 2026-08-16 项目审计修复总纲

> 历史记录：对应批次已经闭环、退役或被后续产品基线取代，本文不得作为当前待办或命令清单。

## 后续处置

`AUD26-021` 后续被明确重分类：搜索页范围 chips 是说明当前搜索覆盖面的装饰文本，不是筛选控件，因此保持不可点击，不再作为未修缺陷。当前交互语义以 Web README 为准。

本文把 [2026-08-16 全项目缺陷审计](2026-08-16-project-audit.md) 转为修复路线。它不授权本轮修改业务代码。

## 目标与非目标

- 先让孵化在检索进程未启动时仍可进入待处理池，并给出能力健康而不是 500。
- 再堵住未发布栏目进入公开读模型。
- 然后收编辑器/发布/导出的错误语义。
- 不恢复 GitHub frozen 工作。
- 不把 18 项并成一份长期 spec。
- 不重开生产 Go 决策。

## 批次

| 顺序 | 批次 | 覆盖 | 是否需要 spec | 目的 |
| --- | --- | --- | --- | --- |
| 1 | 检索不可用是能力态 | AUD26-016、018、019、020、028 | 是（公开/后台行为 + 错误码） | overview/health 200；工作台不被第三进程拖死 |
| 2 | 公开栏目读修订 | AUD26-017 | 是（公开正确性） | 未发布 PATCH 不再改公开筛选/计数/卡片栏目 |
| 3 | 编辑器与发布语义 | AUD26-022、023、025、026 | 是（发布契约） | slug/409/version/导出与文档一致 |
| 4 | 回收站与孵化残留 | AUD26-024、027、029、030、033、035、036 | 024/030 是；其余否 | 删得掉或说得清；预览不再撒谎 |

同源但未单独开卡、修 023 时应一并看：栏目/标签 `useAsyncData` 缓存不刷新、粘贴图片未完成就发布占位注释。

## 批次 1：检索不可用是能力态

目标：`GET /admin/incubator/overview` 与 `GET /admin/incubator/retrieval/health` 在 `:8101` 拒绝连接时返回 200，`health[]` 出现 `retrieval`/`retrieval_service` 的 `blocked` + `RETRIEVAL_UNAVAILABLE`。Worker 离线模型保持不变。`IncubatorShell` 在 overview 失败时仍渲染子页导航，或根本不再把健康检查当成整页失败。预览把 `RETRIEVAL_UNAVAILABLE` 与 `LOCAL_MODEL_NOT_READY` 分开。Worker 记录检索错误码而不是 `INTERNAL_ERROR`。

验收：

- 测试夹具增加「`retrieval_service_url` 指向关闭端口」一条，overview 200、health 含 blocked。
- 已登录浏览器：只起 API+Web，`/admin/incubator/inbox` 能列出 sources，不出现整页 500。
- `failure-state-contract` 继续禁止把 overview 5xx 画成「没有待办」。

## 批次 2：公开栏目读修订

目标：`_revision_category`、`GET /articles?category|tag`、`GET /taxonomy` 计数只使用发布修订上的栏目/标签。工作副本改栏目只影响管理编辑器与 `has_unpublished_changes`。

验收：发布在栏目 A → PATCH 到 B 且不发布 → 公开详情/列表/taxonomy 仍是 A；更新发布后才变成 B。补一条 pytest，禁止只测「发布当时」的快照。

## 批次 3：编辑器与发布语义

目标：已发布 slug 只读。slug 409 不得显示「服务器上已有更新」。文章 `POST /publish` 携带并校验 `version`。`ArticleEditor` 次级加载走 `useApiFailure`；空参考不得在填完前自动 PATCH。导出 ZIP 对已发布内容写当前修订。

验收：对已发布文章改 slug，界面拒绝或保存失败文案含「已发布地址不可改」。双标签页发布与项目发布一样 409。导出文件正文等于公开 API 正文。

## 批次 4：回收站与孵化残留

目标：已发布文章的永久删除要么级联清理修订并成功，要么在确认框前说明不可删。草稿详情渲染 `error`。重构预览在旗标为假时对比当前修订标题。发布计划确认在执行前崩溃后可恢复或明确失败。已发布预览横幅不再写「未公开草稿」。

验收：各条有对应单测或失败态契约扩展。P3（JSON-LD 绝对 URL、「全部文章」计数）可与本批一起改，不单开 spec。
