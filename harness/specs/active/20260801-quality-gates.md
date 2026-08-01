---
id: spec-20260801-quality-gates
level: L1
summary: 以可重复命令固化第三阶段的 WCAG AA、Lighthouse、类型、测试和构建门禁
load_when:
  - task:20260801-quality-gates
author: Gavin
task_id: 20260801-quality-gates
status: verified
---

# Quality gates

## Context

产品基线要求 WCAG AA，并以 Lighthouse 四项 90+ 为目标；当前项目虽然执行类型、Vitest、Playwright 与生产构建，但没有自动化 WCAG 扫描、明确 Lighthouse 阻断阈值或单一发布前质量命令。第三阶段需要把目标变成机器可执行契约。

## Goal

开发者可以用一个跨平台命令对生产构建执行完整 Web 质量门禁，并在可访问性、性能、最佳实践、SEO 或既有回归下降时得到明确失败。

## Non-goals

- 取代人工辅助技术测试、真实用户研究或线上真实用户监控。
- 承诺所有页面在所有设备上绝对达到同一实验室分数。
- 建立 CI、部署平台或提交钩子。
- 修改 API、数据库或认证边界。

## Acceptance criteria

- 新增根级 `quality:web` 命令，顺序执行类型检查、Vitest、生产构建和生产预览质量测试。
- axe-core 以 WCAG 2.0／2.1 A 与 AA 标签扫描首页、归档、关于和搜索页，阻断任何规则违规。
- Lighthouse 在生产预览桌面首页运行；Performance、Accessibility、Best Practices 与 SEO 四项均以 90 分为阻断下限。
- 质量测试复用 Playwright 浏览器与独立测试数据库，不要求系统预装 Chrome，也不污染开发数据库。
- 常规 `test:e2e` 保持业务旅程职责，质量门禁使用独立配置和单 worker，避免性能审计并发噪音。
- README 与 Web 边界记录质量命令和阈值；生产构建警告不被误报为成功门禁失败。

## Risks

- 开发服务器会扭曲 Lighthouse 结果，因此质量审计只针对已完成的生产构建与 preview 服务。
- 实验室性能存在波动，因此只审计稳定首页、串行执行，并以产品目标 90 作为下限。
- axe 自动扫描不能覆盖全部 WCAG 条款，因此验收只声明自动化基线，不替代人工检查。
- 新增质量依赖会增加安装体积，因此只作为开发依赖并锁定在现有 npm lockfile。

## Verification plan

- 先添加会因缺失依赖与配置失败的质量测试入口，再安装最小依赖和实现独立 Playwright 配置。
- 执行 `npm run quality:web`，记录四项 Lighthouse 分数和 axe 扫描结果。
- 再运行常规 E2E，确认质量配置没有改变业务回归行为。
- 刷新 harness 索引并运行 `python -m tools.harness verify 20260801-quality-gates`。

## Implementation record

- 根级 `npm run quality:web` 已串联 Nuxt typecheck、Vitest、生产构建与独立生产预览质量测试。
- axe-core 使用 WCAG 2.0／2.1 A 与 AA 标签扫描 7 个公共页面，最终零自动化违规。
- Lighthouse 使用官方桌面配置审计生产首页；Performance、Accessibility、Best Practices 与 SEO 最终均为 100，超过四项 90 阈值。
- 常规 Playwright 仍使用开发服务验证业务旅程，独立质量配置使用生产 preview、单 worker 和 Playwright 自带 Chromium。
- 测试依赖 `happy-dom` 已升级至安全版本；`npm audit` 当前为零漏洞。
- 完整 `quality:web` 与 3 条业务／SEO E2E 旅程通过。
- Spec 保留在 active 目录：仓库仍无 Git HEAD，无法满足 deterministic close 的历史前置条件。
