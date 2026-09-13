---
id: decision-bounded-list-pagination
level: L1
summary: 高增长数组列表使用有界 offset 分页并由完整消费者显式分批读取
load_when:
  - list-api-change
  - cross-stack-change
  - architecture-decision
author: Gavin
---

# Decision 0005: Bounded list pagination

## Status

Accepted.

## Decision

高增长列表保留数组响应，并统一接受有界的 `limit` 与 `offset`。常规内容列表默认返回 20 条、单次最多 100 条；搜索单次最多 50 条。查询使用时间字段降序和 ID 降序的确定性顺序，并在数据库层执行分页。

交互页面请求比展示数量多一条来判断是否存在下一页。首页和 RSS 明确请求固定数量；站点地图与关系选择器等完整消费者以 100 条为批次读取到空或不足一批。回收站使用 SQL 联合查询后全局排序和分页。

## Consequences

- 单次数据库结果、响应体和页面渲染规模都有硬上限，现有数组消费者无需迁移到新 envelope。
- API 不提供总数，界面只能表达上一页和下一页；以后若需要随机跳页或精确计数，应建立独立契约。
- offset 分页不提供并发写入快照一致性，但稳定次序适合当前单管理员、低写入频率产品。
- 必须完整读取的消费者承担循环请求逻辑，不能依赖列表默认值。
