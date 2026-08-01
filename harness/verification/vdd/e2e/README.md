---
id: vdd-e2e
level: L1
summary: 使用 Playwright 验证核心用户闭环
load_when:
  - user-journey
  - release
  - cross-stack-change
author: Gavin
---

# E2E verification

优先覆盖登录、草稿自动保存、预览、发布、公开阅读、搜索、回收站与 Markdown 导入导出等高价值闭环。测试应围绕用户可见结果，而不是内部实现细节。

