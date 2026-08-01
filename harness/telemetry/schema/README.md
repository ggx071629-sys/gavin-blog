---
id: telemetry-schema
level: L2
summary: 原始 observation-only JSONL 事件的结构定义
load_when:
  - telemetry-implementation
  - telemetry-schema-change
author: Gavin
---

# Telemetry schema

每行必须符合 [telemetry.schema.json](telemetry.schema.json)。Schema 刻意不包含动作建议或决策字段，以维持 observation-only 边界。

