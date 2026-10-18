---
id: decision-media-write-consistency
level: L1
summary: 媒体派生文件批量发布，并在数据库失败时执行 key 级补偿删除
load_when:
  - media-storage-change
  - persistence-change
  - architecture-decision
author: Gavin
---

# Decision 0003: Media write consistency

## Status

Accepted.

## Decision

`MediaStorage` 以单个服务端随机 key 批量接收媒体派生文件。本地适配器在媒体根目录内创建唯一暂存目录，全部文件写入成功后用同文件系统目录重命名发布；失败时清除暂存目录。

应用先 flush 数据库以获得稳定媒体 ID，再发布文件，最后提交数据库。提交前任何失败都回滚数据库，并对本次 key 执行幂等补偿删除。成功提交是清理边界：提交后的响应读取失败不能删除已经持久化的媒体。

## Consequences

- 正常异常路径不会留下部分派生文件、孤儿数据库记录或孤儿最终目录。
- 存储适配器必须提供批量写入和幂等 key 删除能力，而不能只暴露逐文件写入。
- 数据库和文件系统之间仍存在进程强制终止窗口；随机 key 防止覆盖，历史孤儿巡检需由后续独立能力处理。
