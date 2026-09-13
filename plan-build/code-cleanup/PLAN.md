# 无用残留清理：计划入口

| 顺序 | 阶段主计划 | 关键前置 | 独立历史目录 |
| --- | --- | --- | --- |
| 1 | [范围复核与验证基线](PHASE-1-SCOPE.md) | 已获实施指令；C1-01 已归档 | [phase-1-scope](completed/phase-1-scope/) |
| 2 | [后端残留清理](PHASE-2-API.md) | 阶段一完成 | [phase-2-api](completed/phase-2-api/) |
| 3 | [前端、依赖与本地产物](PHASE-3-WEB.md) | 阶段二完成 | [phase-3-web](completed/phase-3-web/) |
| 4 | [联调、启动验证与收尾](PHASE-4-VERIFY.md) | 阶段三完成 | [phase-4-verify](completed/phase-4-verify/) |

四阶段已完成，收尾见 [C4-04](completed/phase-4-verify/C4-04.md)；[正式 spec 已确定性归档](../../harness/specs/archive/20260911-code-cleanup.md)。最终输入 1e6b597 的 76 条精确引用、15 项检查通过。真实 Web/API/worker/E5/Qdrant、当前公开资料读取和 GSAP 浏览器检查通过，现存数据及索引保留，服务已正常停止。

后续更正（2026-09-11）：原收尾将[既有 FTS 覆盖缺口](review/C4-STARTUP.md#真实环境验收与既有遗留)列为保留事项，未完成完整性验收。现由[索引完整性修复](../index-integrity/PLAN.md)修复跨代删除根因、补齐16条FTS，真实当前资料/规范切片/FTS/向量逐条对账通过；原清理证据保留历史。历史待切换代次和失败任务继续保留，未调用付费 Chat、重建或切换索引、运行全量 release 或部署。
