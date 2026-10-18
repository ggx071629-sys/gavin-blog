# 阶段三：前端、依赖与本地产物

## 总体进度

- 完成：5/5；当前任务：无；总体状态：完成。
- 保留 GSAP、ScrollTrigger、orb-motion.ts 与现有悬浮球功能；不替换动画实现，不删动效回归测试。
- 保留 packages/contracts 全部有效生成链和账号/简历消费者；静态资源不能只靠文件名搜索判定用途。
- 状态采用：未开始、进行中、阻塞、未验证、完成；完成必须具有相应验证结论和归档。

## 任务清单

以下业务路径相对 apps/web/；依赖任务同时涉及仓库根目录。

| 编号 | 任务名称 | 状态 | 关键前置 |
| --- | --- | --- | --- |
| C3-01 | 清理 utils/assistant/origin.ts:assistantApiUrl、errors.ts:AssistantUiState，以及 types/api.ts 的四个未使用类型 | 完成 | C2-04 |
| C3-02 | 处置 articlePath/articleFilterQuery、parseAssistantTasks、assistantStorageIsClean/shouldWipeOnPageShow；将 splitSseForTest 按用途迁入测试辅助 | 完成 | C3-01；测试专用与遗漏接入已区分 |
| C3-03 | 移除未使用 @gsap/react 并更新锁文件，保留有效 gsap 依赖及实际消费者 | 完成 | C3-02；依赖 SDD 前置完成 |
| C3-04 | 核实 og/gavin-notes-default.svg 用途和 127.0.0.1 生成目录归属，处置确认无用的产物 | 完成 | C3-03；资源引用与路径安全已确认 |
| C3-05 | 同步受影响文档，执行类型、单元、构建及动效回归并交接 | 完成 | C3-04 |

## 当前任务

本阶段完成。

下一入口：[阶段四 C4-03](PHASE-4-VERIFY.md#当前任务)；C4-01/02 共用本次最终验证结果，不重复运行。

维护：逐项验证通过后归档；未完成项不提前标完成，现行保留边界继续有效。

## 简短验收说明

- 沿用[助手状态反馈](../../apps/web/README.md#公开问答与管理试问)及[动效与无障碍](../../apps/web/README.md#公开问答与管理试问)的适用条件；旧设计入口外形不覆盖现行悬浮球与本次 GSAP 保留指令。
- parseAssistantTasks 只有测试调用，须判明旧接口残留还是现行校验遗漏；不要为消除“死代码”盲目接入旧 parser，新行为走 SDD。
- splitSseForTest 是有效测试辅助；不得以迁移为由删除 SSE 分片覆盖，其他测试专用函数按真实用途处置。
- C3-04 不删数据库、媒体、正在使用的日志/构建产物；核验 Windows 绝对目标在工作区内，无法确认则保留并记录。
- C3-05 沿用现有类型、lint、构建及 orb-motion/discovery 等受影响检查；不增加新的视觉或性能阈值。

## 已完成事项


- [C3-01：未消费函数与手写类型](completed/phase-3-web/C3-01.md)：验证通过，已归档。

- [C3-02：工具清理、SSE 迁移与获批合同同步](completed/phase-3-web/C3-02.md)：验证通过，已归档。

- [C3-03：移除未使用 React GSAP 适配依赖](completed/phase-3-web/C3-03.md)：验证通过，已归档。

- [C3-04：资源和本地产物保留决定](completed/phase-3-web/C3-04.md)：验证通过，已归档。

- [C3-05：前端收尾与现行动效验证](completed/phase-3-web/C3-05.md)：验证通过，已归档。
