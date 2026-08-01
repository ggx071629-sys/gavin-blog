---
id: vdd-integration
level: L1
summary: 验证 FastAPI、SQLite 与外部边界的协作
load_when:
  - backend
  - persistence
  - integration
author: Gavin
---

# Integration verification

验证 API 路由、服务、SQLAlchemy、SQLite FTS5、认证 Session 和媒体适配器之间的真实协作。使用隔离数据库，不依赖生产基础设施。

