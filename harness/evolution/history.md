---
id: evolution-history
level: L1
summary: 已终结 Evolution proposal 的按需审计入口
load_when:
  - process-evolution-history
  - evolution-audit
author: Codex
---

# Evolution history

主 [Evolution 索引](INDEX.md) 只保留 policy、这个历史入口以及尚未终结的 `proposed` 或 `accepted` proposal。`applied`、`reviewed-no-action` 与 `rejected` 属于冷审计历史，不进入普通 process-evolution 路由。

需要追溯人工决定、实施结果或无行动依据时，再打开生成的 [proposal 历史索引](proposals/INDEX.md)。历史降级只改变发现路径，不删除、移动或重写 proposal 与 event。
