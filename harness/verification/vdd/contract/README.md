---
id: vdd-contract
level: L1
summary: 验证 OpenAPI、数据库迁移和前后端共享契约
load_when:
  - api-change
  - schema-change
  - cross-stack-change
author: Gavin
---

# Contract verification

验证 OpenAPI 兼容性、生成契约是否同步、Alembic 迁移链是否完整，以及 Web 与 API 对字段和错误语义的理解是否一致。

