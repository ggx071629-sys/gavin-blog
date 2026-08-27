---
id: review-2026-08-15-project-audit-remediation-plan
level: L2
summary: 已闭环的 2026-08-15 项目审计历史修复计划
load_when:
  - historical-audit
  - audit:2026-08-15
author: Grok
---

# 2026-08-15 项目审计修复总纲

> 历史记录：对应批次已经闭环或被后续产品基线取代，本文不得作为当前待办或命令清单，包括其中的 worktree 清理示例。

本文把 [2026-08-15 全项目缺陷审计](2026-08-15-project-audit.md) 转为修复路线。它不授权本轮修改业务代码。

## 目标与非目标

- 先修公开阅读壳层误导文案，再补后台失败态，最后改配置注释与本机残留。
- 不恢复 GitHub frozen 工作。
- 不把 4 项缺陷并成一份长期 spec。
- 不重开生产 Go 决策。

## 批次

| 顺序 | 批次 | 覆盖 | 是否需要 spec | 目的 |
| --- | --- | --- | --- | --- |
| 1 | 阅读壳层文案 | AUD26-004 | 是（公开可见行为） | 去掉实现词，读者只看到中文相关标题 |
| 2 | 后台失败态 | AUD26-003 | 是（失败分类契约） | 孵化与编辑页不再把 5xx 显示成空成功 |
| 3 | 配置文档 | AUD26-005 | 否 | 让 `.env.example` 与已交付生成能力一致 |
| 4 | 本机残留 | AUD26-001 | 否 | 注销多余 worktree；不改产品代码 |

## 批次 1：阅读壳层文案

目标：相关区与信号轨使用读者语言。建议「相关文章」；不要输出 `adaptive`。`Article signal` 要么中文化，要么删掉。

验收：有 1 条和多条相关文章的公开阅读页不再出现 `adaptive`；e2e 增加否定断言。

## 批次 2：后台失败态

目标：孵化概览、工作台壳、文章/项目/书摘/名片编辑在 API 失败时走与公开页相同的失败分类，禁止「没有待办」和空白编辑器。

验收：扩展 `failure-state-contract` 与 failure-state Playwright；API down 时 `/admin/incubator` 不出现 `attention-empty` 成功文案。

## 批次 3：配置文档

删除「本阶段不调用生成模型」。补 `GAVIN_LLM_GENERATION_MAX_OUTPUT_TOKENS` 并与默认 2048 对齐。

验收：`.env.example` 与 `config.py` / 草稿生成路径一致。

## 批次 4：本机残留

```powershell
git worktree remove --force C:\Users\Administrator\AppData\Local\Temp\gavin-publish-iso\worktree
```

若目录已脏，先确认不是正在使用的隔离验证。不要把它写成产品 bug 修复 PR。
