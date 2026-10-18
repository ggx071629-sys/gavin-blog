---
id: workflow-verify
level: L1
summary: 用 VDD 与机器证据验证变更，而非依赖自然语言自证
load_when:
  - verification
  - implementation
author: Gavin
---

# Verify

- Input：实现、active spec 和 `harness/verification/impact/<task_id>.json` 独立影响计划。
- Scope：在 ownership.json 登记细粒度单元、源码归属、case 和已知消费者；逐文件说明影响，平铺记录每个可达消费者的 affected 与理由，仅沿 affected 消费者继续审查传递影响。循环不重复，未知、歧义、遗漏与不可达判断均阻断。普通文档需显式说明结构影响；可执行合同文档还需审查消费者。
- Preconditions：先提交 spec 并运行 spec-lint；该检查不提前要求未来 case 与完整影响计划。集中完成实现和审查，准备所需 pending evidence 链接占位、case、归属、文档、计划及生成索引，再提交验证输入。检查相关文档目标、源码及计划无工作区漂移。required 文档目标必须在 spec 首次提交后有已提交变化；失败不启动测试。
- Plan/status：只读解释所选 case、排除理由、门禁、复用与失效原因；不启动产品测试、构建或 collector。`plan <task> --json` 输出完整影响分析。
- Snapshot：工作区结构结果标记为 workspace；固定 HEAD 隔离检出后，任何依赖链接、初始化、收集和产品测试之前检查提交快照及完整任务计划。失败时消费者 not-run；成功检查承担本轮 harness-integrity，close 的事务前后检查仍执行。
- Diagnose：`diagnose <task> --case <case>` 或 `--failed` 仅执行当前完整计划的精确子集。首版固定 HEAD；可信失败记录缺少消费者、引用消失或歧义时报告 gap。诊断产物留独立本地命名空间，不能覆盖正式 evidence/aggregate，不能关闭任务。
- Task verify：`python -m tools.harness verify <task>` 先执行廉价结构检查，再执行计划的 exact refs。全局 module-coverage 只检查合同结构、归属和文件；实际收集属于所选 runner。Pytest 使用 node ID，Vitest 使用文件与名称，Playwright 使用 spec、config、project 与名称；不调用整套 npm quality 脚本。
- Profiles：普通 focused/stack 不再有按目录固定的全应用门禁下限。全量 release 只属于明确发布任务；选择 release profile 表示独立发布政策，不能通过脚本/配置的文件位置自动推导。
- Fresh：`--fresh` 只重新执行所选范围。复用默认关闭，默认不探测安装分发；普通有测试任务使用 `verify <task> --close`。只有明确有界输入合同且检查成本有收益时才启用复用；未登记安装依赖闭包时，不允许跨进程复用或关闭。
- Isolation：所选检查在固定 HEAD 的 detached 临时 worktree 执行，只链接所需依赖，不自动安装。所选生产预览测试才构建其需要的 Web 产物。清理失败、中断、来源不完整不得发布可关闭的 passed evidence。
- Attempts：保留失败与未执行状态；同输入最新失败不能被旧成功覆盖。受控环境屏蔽任意应用密钥和测试参数；端口冲突只报告占用者，不终止其他任务。失败日志在清理前导出到本机有界目录。
- Reporting：成功输出范围、结果和耗时；失败输出诊断和日志位置。收集、执行、复用及输出字节分别计数，不用字节数冒充 token。
- Close：消费认证 evidence，不启动产品测试、构建或 collector。可在最终 runner 完成后用 `verify <task> --close` 同进程消费。原始 spec 保留于 Git 历史；archive、completion event 和 exact evidence digest 由事务创建，失败回滚。
- Complete when：最终输入适用、真实 runner 来源、全部 AC 的所选检查及隔离清理均通过。commit/verify/close 只是步骤，不机械增加一轮相同测试。

细节与信任边界见 [受影响范围决策](../docs/decisions/20260905-verification-resume.md)。

执行阶段、完整身份与数据隔离合同见 [执行合同决策](../docs/decisions/20260906-harness-execution.md)。默认保持单身份浏览器隔离与 `merge_playwright=false`，成本门槛达成后才开放显式共享批次。
