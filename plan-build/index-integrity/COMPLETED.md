# 索引完整性修复：完成记录

2026-09-11 完成；任务 `20260911-index-integrity`。

根因是不同代次共享稳定chunk_id，而FTS删除未限定generation。现已限定单代删除；独立从当前公开来源推导预期切片，逐条检查规范数据、FTS与Qdrant的身份、版本、正文和向量绑定。真实启动、构建ready与finalize均以完整性检查失败阻断。

真实修复与验收使用实现提交 `1934eef60a82d95bc25daa3205ebfe98f82f5753`，见[真实证据](REAL.json)。备份后事务补齐active第14代16条FTS，覆盖从9/25恢复为25/25；5份当前公开来源对应25条预期切片，各层逐条零差异。重复修复零变更，全部11个Qdrant集合与其他代FTS摘要不变。未重算或写入向量、创建或切换代次、重试历史任务、调用付费Chat。

真实Web/API/worker/E5/Qdrant通过，nginx和codex恢复关键词双路命中，引用可恢复到当前版本，简历PDF哈希一致。既有GSAP浏览器用例在真实服务上通过，覆盖暂停、减少动态效果、导航清理及响应式等行为。运行后仅预期的心跳、统计及运行状态变化，服务正常停止，五个端口释放。

正式验证输入 `3d219cf`，执行 `python -m tools.harness verify 20260911-index-integrity --close`：10个case、50条精确引用、13项检查全部通过，三个AC均passed，验证耗时42.502秒；306个无关case按影响排除。新增完整性回归包含24条精确测试身份，覆盖跨代隔离、逐层破坏检测、备份、回滚、幂等、启动/切换阻断及本机/容量消费者。没有执行全量release。

[正式证据](../../harness/verification/evidence/20260911-index-integrity.json) SHA-256：`c2bad8e9f359c246c7bdf46cc7e53dfed89b652570c32e634965caa4596ccb49`。同进程close事务前后结构检查各9项通过；关闭时间 `2026-09-11T13:02:54.865305+00:00`。生成[确定性归档](../../harness/specs/archive/20260911-index-integrity.md)及[完成事件](../../harness/evolution/events/20260911-index-integrity--spec-completed.json)，原spec保留于Git历史。

原C4记录保留历史，并补充此解决结果。完整性结论针对当前公开资料及active索引，不代表任意问题的语义召回保证；历史第15代待切换及旧失败任务继续保留。原始日志、备份和摘要留本机 `.run/index-integrity/`，仓库只保存紧凑证据。此任务无剩余验收项。
