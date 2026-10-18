# 阶段二：后端残留清理

## 总体进度

- 完成：4/4；当前任务：无；总体状态：完成。
- 仅处理经复核无使用路径的残留；不借清理改变检索、预算、清理策略、认证或存储边界。
- 更正 C1-01：_Gen 被 assistant/runtime.py:64 延迟导入，必须保留；只删除无调用 _generation_stub。
- 保留历史迁移、incubator 兼容枚举、runtime_models 的元数据注册和有效 CLI 入口。
- 状态采用：未开始、进行中、阻塞、未验证、完成；完成必须具有相应验证结论和归档。

## 任务清单

以下位置均相对 apps/api/app/；列出的函数需要先复核，再执行处置。

| 编号 | 任务名称 | 状态 | 关键前置 |
| --- | --- | --- | --- |
| C2-01 | 清理 assistant/store.py 的 public_completed_turn、clear_transient、count_live_subscribers、estimate_bytes | 完成 | C1-03 |
| C2-02 | 清理 assistant/readiness.py 的 _generation_stub/_Gen；hydrate.py:recheck_evidence、money.py:micro_to_cny、pragmas.py:begin_immediate、routes.py:_cache_headers、runner.py:_lease_token、runtime_schema.py:index_names/runtime_file_paths | 完成 | C2-01 |
| C2-03 | 处置 assistant_index/worker.py:_abandon_generation/switch_generation、routes/admin_content.py:trash_item、search.py:rebuild_search_index | 完成 | C2-02；维护入口用途明确 |
| C2-04 | 清理伴随失效引用、验证后端并交接 | 完成 | C2-03 |

## 当前任务

本阶段完成。

下一入口：[阶段三 C3-01](PHASE-3-WEB.md#当前任务)。

维护：逐项验证通过后归档；未完成项不提前标完成，现行保留边界继续有效。

## 简短验收说明

- 沿用[助手共同约束](../assistant-upgrade/ASSISTANT-UPGRADE-DESIGN.md#4-共同约束与适用验收)，保留公开版本、引用、会话及运行库隔离语义。
- C2-03 的搜索重建函数可能是手工维护工具；无仓库调用不是充分删除依据，须确认用途或保留并说明。
- 后端 Ruff 与精确 Pytest refs 由影响计划选择；不为已删函数保留“只证明自己”的测试，不删除保护现行业务的测试。
- C2-04 核对路由和 schema 无意外变化；不操作真实数据库、媒体、向量集合或迁移历史。

## 已完成事项


- [C2-01：运行库工具残留](completed/phase-2-api/C2-01.md)：验证通过，已归档。

- [C2-02：内部函数清理与延迟消费者修正](completed/phase-2-api/C2-02.md)：验证通过，已归档。

- [C2-03：索引与回收站残留](completed/phase-2-api/C2-03.md)：验证通过，已归档。

- [C2-04：后端契约与交接](completed/phase-2-api/C2-04.md)：验证通过，已归档。
