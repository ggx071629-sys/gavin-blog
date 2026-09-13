# 阶段 F：本机真实问答验收归档

2026-09-06 完成。返回 [主计划](../build-qa.md)。

- 显式入口：根目录 `npm run dev:assistant:real`，真实 E5 + DeepSeek；签名本机 probe/readiness、持久 runtime 与费用。生产资格保持独立。
- 真实中文、英文跨语言证据、连续追问、引用恢复和证据不足测试完成；修复多段引用误拒、空 blocks 重试、租约唯一约束与异步 saver 锁等待。
- 最终双并发 HTTP 均 200，分别为带引用回答和证据不足，1.546/3.738 秒。DeepSeek/Codex 配置题的正向覆盖未证明，保留质量限制；不把拒答计为答对。
- 总保守费用 0.094950 元（测试批准上限 1 元，Chat 日上限 2 元）；含未知请求按最高费用计入的 0.028608 元。真实提交共 14 次、准入 12 轮；修复后补测仍在同一批准预算内，没有清空账本。
- 最终采样 71 点：API 工作集峰值约 531 MiB，私有分配约 994 MiB，短时峰值约 0.52 个本机逻辑核。相对 D 阶段的内存增量保守界约 59 MiB；完整规划 7–8 GiB 内存、3 个同档逻辑核留量、约 12 GiB 应用磁盘。
- F 仅四角色与开发 Web，完整估算复用 D 的五角色基线；CPU 叠加可能重复计数。未做长时 soak、生产部署、HTTPS edge、2 核 / 4 GB VM 验收。
- 自动化故障与回归：15 项检查、30 个精确引用全部通过，包含 E5/Qdrant 故障注入后的 FTS、Chat/预算、迁移/双图、DELETE/清理、引用恢复与浏览器定位。
- 测试 Web/API 已停止；原有模型、Qdrant 与持久数据保留。零活动租约、零 checkpoint/writes 残留、零费用预留。

证据：[Harness 归档](../../../harness/specs/archive/20260906-local-real-qa.md)、[精确测试 manifest](../../../harness/verification/evidence/20260906-local-real-qa.json)、[真实链路与资源 manifest](../../../harness/verification/evidence/20260906-local-real-qa.benchmark.json)。维护、预算、索引、启停与回滚见 [操作交接](../../../harness/docs/operations/local-real-qa.md)。
