---
id: spec-20260911-assistant-resume-source
level: L1
summary: 以可信 PDF 链接和显式刷新为问答助手提供可撤销版本化简历证据
load_when:
  - task:20260911-assistant-resume-source
task_id: 20260911-assistant-resume-source
status: active
verification_profile: focused
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - apps/web/README.md
  - packages/contracts/README.md
  - harness/docs/architecture/boundaries.md
documentation_reason: 记录可信下载与解析执行边界、PDF 内容库所有权、手动刷新和版本化公开引用。
state_history:
---
# Context
执行阶段三 Q3-01—Q3-07，依赖关于页接入完成。依据 ASSISTANT-UPGRADE-CONTRACT.md、completed/assistant-upgrade-design/Q1-02.md。用户最终要求首次/换址自动导入，同址更新手动刷新；此前小时级检查方案已撤回。
# Goal
让后端有界下载、提取并索引允许公开的 PDF 简历，提供真实刷新状态和后端绑定的版本化文件引用，复用既有 RAG 与运行边界。
# Non-goals
无定时检查、时间过期、OCR、人工预览确认、正文网页、任意网址抓取、新常驻服务、额外对话留存、付费验证或部署；保留原“查看简历”。
# Acceptance criteria
- AC-1: 仅配置可信 HTTPS 目标可下载，每跳校验并将连接绑定已校验公网地址；拒绝私网、未授权重定向、超限及超时，错误无原文和秘密。
- AC-2: 只解析未加密且可提取文字的 PDF；页数/内存/时间/输出限额由 worker 所有的有界短生命周期子进程执行，无法强制边界时失败关闭；不执行附件或访问网络/数据库。
- AC-3: 内容 SQLite 保存 PDF、提取文本和版本绑定；相同 hash 复用结果，换址/清空及新版失败撤销旧资格并清理缓存；迟到任务不能写回或混用版本，备份与恢复责任明确。
- AC-4: 仅首次/换址/手动操作触发下载，有限重试可恢复；成功版本不按时间过期，检查失败暂停证据，成功同 hash 恢复不重复解析；worker 不运行周期检查。
- AC-5: 个人资料页显示真实阶段和最后成功检查时间；刷新通过 Session/CSRF/绑定版本与冷却合同，排队不冒充同步，手机/键盘/双主题操作可达。
- AC-6: 简历参与既有混合检索与预算，引用仅打开对应后端 PDF 版本，失效版本拒绝访问；资料冲突引用双方，不可用时仍回答其他来源支持部分；保留会话与迟到发布边界。
- AC-7: 隔离夹具导入、更新、失败、撤销及可点击引用闭环通过；真实文件结果独立记录，缺少真实输入不能宣称真实导入或生产就绪。
# Risks
新增网络读取含 SSRF/DNS 重绑定风险；PDF 压缩体积不能约束解析资源；SQLite BLOB 增加备份体积；公开下载不能撤回已交付副本；约束执行平台必须实测。网络/解析子进程不继承应用秘密、数据库句柄或任意代理。实际简历未提供，只能先验收夹具。
# Verification plan
## Verification cases
- AC-1 => M06-RESUME-DOWNLOAD-01, M06-RESUME-DOWNLOAD-LIMITS-01
- AC-2 => M06-RESUME-PARSE-01, M06-RESUME-PARSE-LIMITS-01
- AC-3 => M06-RESUME-STORAGE-01, M06-RESUME-FENCE-01, M10-RESUME-INDEX-01
- AC-4 => M06-RESUME-REFRESH-API-01, M06-RESUME-REFRESH-WORKER-01, M06-RESUME-REFRESH-RETRY-01
- AC-5 => M06-RESUME-ADMIN-UI-01, M06-RESUME-REFRESH-API-01
- AC-6 => M09-RESUME-FACTS-01, M06-RESUME-PDF-01, M09-RESUME-CITATION-UI-01
- AC-7 => M06-RESUME-REFRESH-WORKER-01, M06-RESUME-REFRESH-RETRY-01, M06-RESUME-PDF-01, M09-RESUME-CITATION-UI-01, M11-ASSISTANT-PROJECTION-01, M11-ASSISTANT-SYNC-01, M09-ABOUT-RETRIEVAL-01, M09-ABOUT-CITATION-01, M09-ABOUT-FACTS-01
## Gates
- api-tests => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- e2e => AC-5, AC-6, AC-7
- harness-integrity => AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
