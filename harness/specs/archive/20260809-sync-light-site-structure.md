---
id: archive-20260809-sync-light-site-structure
level: L2
summary: 以暗色主题为规范统一全站浅色页面的布局、卡片结构与形状系统
load_when:
  - task:20260809-sync-light-site-structure
author: Gavin
task_id: 20260809-sync-light-site-structure
status: compressed
restoration_source: "fa89a6a2a1906ec9f80e596f5906d9ed54ccc52f:harness/specs/active/20260809-sync-light-site-structure.md"
restored_at: 2026-08-11
---

# 20260809-sync-light-site-structure

Deterministic compressed record. The original active spec remains in Git history.

## Goal

以现有暗色主题的 Electric Editorial 结构为全站唯一布局规范，让浅色主题复用相同的首页网格、卡片层级、圆角尺度和阴影几何；浅色继续使用自己的画布、表面、文字、边框、状态色和较低阴影透明度。

## Acceptance criteria

1. 根主题使用暗色规范的 `--ee-radius: 4px` 与 `--ee-radius-soft: 8px`，暗色不再重复覆盖这两个结构令牌。
2. 浅色浮层阴影与暗色使用相同的 `0 18px 45px` 几何层级，但保留适合浅色背景的较低透明度。
3. 桌面首页浅色与暗色共同使用 9/3 网格：主介绍与最近文章占前 9 栏，个人卡片占后 3 栏并跨两行，首篇文章不再只在浅色跨两列。
4. 桌面文章列表浅色不再清除卡片背景及三侧边框，复用与暗色相同的完整卡片结构和共享圆角。
5. 搜索、文章／项目／读书详情、归档、关于、404、公开列表及管理页面不存在主题专属的间距、网格、显示、尺寸、圆角或边框存在性规则；主题差异仅保留颜色、阴影透明度及其他不改变信息结构的视觉令牌。
6. 自动化守卫覆盖 CSS 结构令牌、主题限定选择器和 Vue `dark:` 结构工具类；浏览器场景覆盖首页、文章列表、搜索与管理登录的桌面双主题结构及移动端无横向溢出。
7. 全量 Web 单测、类型检查、生产构建和现有全站质量矩阵通过，或明确区分并报告与本任务无关的既有失败。

## Result

Verified and closed by the harness close command.

## Evidence

[20260809-sync-light-site-structure.json](../../verification/evidence/20260809-sync-light-site-structure.json)

Closed at 2026-08-09T13:05:47.204918+00:00.
