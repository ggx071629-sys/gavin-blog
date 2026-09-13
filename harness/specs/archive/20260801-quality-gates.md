---
id: archive-20260801-quality-gates
level: L2
summary: 以可重复命令固化第三阶段的 WCAG AA、Lighthouse、类型、测试和构建门禁
load_when:
  - task:20260801-quality-gates
author: Gavin
task_id: 20260801-quality-gates
status: compressed
---

# 20260801-quality-gates

Deterministic compressed record. The original active spec remains in Git history.

## Goal

开发者可以用一个跨平台命令对生产构建执行完整 Web 质量门禁，并在可访问性、性能、最佳实践、SEO 或既有回归下降时得到明确失败。

## Acceptance criteria

- 新增根级 `quality:web` 命令，顺序执行类型检查、Vitest、生产构建和生产预览质量测试。
- axe-core 以 WCAG 2.0／2.1 A 与 AA 标签扫描首页、归档、关于和搜索页，阻断任何规则违规。
- Lighthouse 在生产预览桌面首页运行；Performance、Accessibility、Best Practices 与 SEO 四项均以 90 分为阻断下限。
- 质量测试复用 Playwright 浏览器与独立测试数据库，不要求系统预装 Chrome，也不污染开发数据库。
- 常规 `test:e2e` 保持业务旅程职责，质量门禁使用独立配置和单 worker，避免性能审计并发噪音。
- README 与 Web 边界记录质量命令和阈值；生产构建警告不被误报为成功门禁失败。

## Result

Verified and closed by the harness close command.

## Evidence

[20260801-quality-gates.json](../../verification/evidence/20260801-quality-gates.json)

Closed at 2026-08-01T16:43:52.963848+00:00.
