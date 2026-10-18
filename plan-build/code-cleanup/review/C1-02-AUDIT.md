# C1-02 人工审计包

状态：人工审计已通过；用户于 2026-09-11 明确“确认C1-02”。以下为获批方案和审计时输入快照。

## 已准备的输入

- SDD：任务 `20260911-code-cleanup`，初始提交 `40b7f6a`；通过 [规格索引](../../../harness/specs/INDEX.md) 定位。`spec-lint` 已通过。
- [独立影响计划](../../../harness/verification/impact/20260911-code-cleanup.json)：32 项预计路径决定，覆盖源码、测试辅助、依赖锁、验证合同和阶段文档。
- [精确引用快照](C1-02-exact-refs.json)：当前合同的 11 个既有 case，经去重为 78 个测试引用及 1 个结构检查。内含原合同 SHA-256；不是已执行证据。最终测试身份仍由 Harness 根据配置、project 和精确测试名解析。
- [审计差异](C1-02-case-changes.patch)：仅供审阅，尚未应用。包含两个 case 的合同调整、对应测试调整及 SSE helper 新位置；必须与后续生产函数删除同批实施，不单独应用成品。
- 归属新增仅为清理文档与未来 `apps/web/tests/helpers/assistant-sse.ts`；已有消费者没有改变。预计影响计划通过 Harness `build_plan(..., paths=预计路径)` 验证：32 paths / 11 cases / 78 test refs / 1 check ref；registry audit 为 91 units / 545 governed paths / 0 errors。

## 为什么此处停下

[验证规则](../../../harness/verification/README.md#module-verification-contract)明确要求：

> Reviewer 在每次新增或修改 case 时必须人工逐条检查 `covers` 对应的断言与正／负预期，不能把测试名、引用存在或总测试数当作语义证明。

本次清理会删除已经登记的两条文章工具测试，并更正一条内存/字数测试的名称及覆盖声明。因此先准备完整差异供人工审计，审计通过前保留产品源码、测试与模块验证合同，不将自检冒充人工批准。

## 需审计的两项合同变更

### 1. M01-UNIT-ARTICLE-01：移除无生产消费者工具的自证覆盖

[当前测试](../../../apps/web/tests/unit/article.test.ts)的 `builds a stable UTC publication path` 只调用 articlePath；`builds public taxonomy filters from supported query values` 只调用 articleFilterQuery。C1-01 已核实真实 [文章卡片](../../../apps/web/components/ArticleCard.vue)读取后端 public_path，[文章列表](../../../apps/web/pages/articles/index.vue)直接使用 route.query 和 Vue query 对象。二者不消费这两个工具函数。

拟同时移除上述两条测试和合同引用，将 case 的正预期收敛至真实保留的 slug 规范化与合法表单，负预期保留非法表单拒绝；不删除生产路由、筛选或其他回归测试。

| 保留的精确测试名 | 实际断言 | 拟 covers |
| --- | --- | --- |
| creates URL-safe ASCII slugs | 带空格/大小写/标点标题规范化为 reliable-agent-harness | E01：正预期 |
| requires an explicit English or pinyin slug when the title cannot generate one | 中文标题配空 slug 返回要求填写 Slug 的字段错误 | E02：负预期 |
| rejects empty titles and slugs outside the API slug contract | 空标题与 Invalid_slug 返回错误；Valid title 与 valid-slug 返回两个空错误 | E01 + E02 |

代价与边界：删除的是未被生产消费的本地 UTC 路径推算和查询串构造测试，不再声称这个单元 case 验证整站路由/筛选。真实路由/筛选仍由既有页面、API 及其未改动测试负责；不能把剩余三条 slug 测试当作它们的替代证明。

### 2. M09-UI-BOUNDARY-01：不以常量/布尔包装测试声称 BFCache 覆盖

[当前单元测试](../../../apps/web/tests/unit/assistant.test.ts)的 `counts unicode code points and wipes on BFCache` 没有触发 BFCache，只检查纯布尔包装、字数、空内存和存储 key。

拟删除对无生产消费者的 shouldWipeOnPageShow、assistantStorageIsClean 的自证断言，保留 `COUNT_POINTS('你好a') === 3` 与空内存的 idempotencyKey 为 null，改名 `counts unicode code points and initializes empty memory`，其 covers 只指向正预期 ALLOW。case 的其他正/负预期保持不变。

真实生命周期覆盖明确保留并选择 `M09-UI-STATES-01`：[panel state recovery](../../../apps/web/tests/e2e-assistant/panel.spec.ts)在第 278 行派发 `pageshow(persisted: true)`，释放迟到 DELETE 后检查旧问题为 0、重新开始可用。生产 [AssistantHost](../../../apps/web/components/AssistantHost.vue)继续直接判断 event.persisted；不删除清除/迟到响应代际隔离逻辑。

SSE 迁移是同一改动中的支持操作：splitSseForTest 函数体原样迁至 tests/helpers，测试改 import。`parses events across arbitrary chunk and CRLF boundaries` 的 `[1, 3, 7, 11]` 分片循环、终止事件与正文断言保持不变，仍由同一 boundary case 引用。生产 AssistantSseParser 不变。

## 其他保持不变的审查决定

- @gsap/react 仅根声明；删除前复核 peer React 是否仍无其他消费者，再由 npm 更新锁文件；不升级 gsap，不合并两处有效声明。
- 保留 switch_generation、rebuild_search_index、parseAssistantTasks、公开 SVG；未确认占用及递归链接安全的 127.0.0.1 目录保留。
- 不新增模块 case，不调低性能、无障碍、安全或构建阈值。预计正式 gates 为 api-tests、web-quality、e2e、harness-integrity；额外 Ruff、Web typecheck/lint 和契约生成比较按阶段作为补充检查，不能冒充 exact-ref 正式证据。

## 执行状态与后续顺序

`plan/status` 已运行，但当前 HEAD 只有初始 spec，尚无实施差异，因此正式 plan 正确报告 11 个 declared case 尚无 HEAD 变更来源；status 为 active、无认证 evidence。预计路径校验通过不能替代正式 HEAD 计划通过，C1-02 未标完成。

审计通过后，按当前合同在固定提交的隔离副本执行 C1-03 基线并明确记录为基线；普通 task verify 不能通过伪造实施路径来充当基线。清理按 C2/C3 分项执行，实施上述差异后重新核对 case/ref（预计减少两条文章专用引用），补齐实际变更与归档文档的逐文件影响分析。最后用最终提交的标准 plan/verify/close 形成正式证据，不复用初始审查结果关闭任务。

隔离要求：API 测试用既有 tmp fixtures，助手 Playwright 配置使用 Web 3101/API 8101、reuseExistingServer=false 并构建预览；复用 Harness 提供的独立 run root 和服务进程管理。若端口被真实问答占用，报告占用，不能终止用户进程或改用真实库。测试和本机启动核对均不自动发起付费问题。

人工审计结论：用户已确认 C1-02，两项合同/断言调整按所附补丁获准实施；保留既有 GSAP、SSE 分片与真实 BFCache 回归，不移除 gate。

## 提交审计前的验证

- Harness 全局结构验证：10 checks 通过（约 3.2 秒），不执行产品测试。
- `git apply --check`：审计补丁可以应用于当前源码；检查没有应用补丁。补丁已统一为仓库要求的 LF。
- `spec-lint`、预计路径影响计划与归属检查通过；正式 plan/status 的未实施阻塞已如实保留。
- 源码、测试、模块验证合同、package/lock 均未改动。没有安装依赖、启动应用、访问真实问答数据或执行修复后产品测试。
