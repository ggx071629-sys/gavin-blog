---
id: decision-public-qa-production-qualification
level: L1
summary: 以真实目标签名证据判定默认关闭的公开问答生产资格
load_when:
  - architecture-decision
  - assistant-online
  - production-qualification
author: Gavin
---

# Decision: evidence-bound public Q&A production qualification

2026-09-06：管理员取消原生产资格任务，直接移除其 spec，不生成完成归档。本文记录已实现的资格控制边界；后续如需推进生产资格，应按当时实际环境重新立项。

## Context

前五阶段已交付本地 RAG、在线内核、Web 消费层、runtime 完整性和管理员运营面，但它们只证明仓库合同与本地行为。替身 provider、OpenAPI、readiness receipt、dashboard healthy 或 release gate 都不能证明最终供应商、公网代理、持久化恢复和 2 vCPU／4 GB 目标主机可安全运行。当前生产平台、域名、provider、模型、备份产品、告警渠道和阈值仍未由管理员选定，不能由实现者补猜。

## Decision

- 唯一状态机是 `LOCAL_READY → QUALIFICATION_GO_CANDIDATE | QUALIFICATION_NO_GO`。只有新鲜 GO candidate 可在任务外进入 `FINAL_GO → PUBLIC_ENABLED`；task close、部署与 runner 都不是最终启用动作。当前状态是 `LOCAL_READY`。
- 管理员先批准一份严格、非秘密且固定 digest 的 production qualification profile。它选择唯一 OS／进程平台、edge、真实 OpenAI-compatible Chat／Embedding、Qdrant、路径、备份、告警、阈值、治理与 secret source；没有选择前不生成通用占位部署资产。
- 生产 API 与 Worker 从绝对 path 加载该 profile，并把内容 SQLite、共同写 fence、media、runtime、Qdrant volume，origin／可信代理／heartbeat，模型版本、限制、价格、三预算、pipeline 和 Qdrant 私网地址逐项绑定。profile 或运行配置漂移均 fail closed。
- 真实 provider probe 默认为零调用，只有管理员显式选择 provider、批准精确 profile digest 和费用 envelope 后才调用。缺 usage 或不可证实身份是 measured fail，并保守结算；不能用字符估算或 operator 配置冒充 provider 事实。
- 目标 runner 必须在批准的 Git 外隔离目录、真实 2 vCPU／4 GB 主机和最终 artifact 上运行固定 47-case suite，其中 32 项是最终系统 conformance。case 只能是 `pass`、真实 `measured_fail` 或有无环因果的 `blocked_by`，不得以 missing、unknown 或未提供环境形成 No-Go。
- 仓库 release／E2E 与目标签名 manifest 是两层证据。前者证明代码合同；后者绑定 source commit、artifact、profile、case suite、真实 target/provider、测量、费用、外部 raw artifact 哈希、TTL 与三开关关闭。qualification 私钥不入 Git，仓库 verifier 只信 pinned public key。
- Qdrant 是同机独立、认证且私网绑定的可重建派生存储。内容 SQLite 与 media 通过共同写 fence 和版本化 manifest 形成一致恢复点；最终备份必须主机故障域外加密。`assistant_runtime` 在普通重启间持久，但连同 WAL／SHM 和 LangGraph checkpoint 排除长期备份；恢复后新 runtime 锁定 Chat／query 到下一北京时间零点。
- pinned `AsyncSqliteSaver` 只作为本地盘、单 API owner、低并发的受限例外。第二 owner、共享网络文件系统、持续锁争用、清理残留或 crash 不变量失败都得到资格 No-Go，并转独立 saver migration spec。
- Chat 的北京时间 2.00 元日 cap 与 query／index Embedding cap 分开，均按 `settled + reserved` 控制，也都不是 provider 总账单保证。provider account 告警必须与本地估算分开呈现。
- CSP 当前真实状态仍为 Report-Only。最终 profile 必须选择强制 CSP，或提供有期限的风险接受与补救引用；应用安全头不能被写成已经强制 CSP。

## Consequences

- 在管理员提供最终 profile、真实目标和受控访问前，生产资格无法判定，当前 production 结论保持 No-Go；这属于信息／环境缺失，不是一次完整的 `QUALIFICATION_NO_GO`。
- 本地备份 helper、target runner、签名 verifier、32-case conformance suite 和启动绑定只是资格控制，不是目标测量。不得因这些工具存在而声称 production-qualified。
- `QUALIFICATION_GO_CANDIDATE` 也不表示已经部署、持续可用或对普通访客开放；`QUALIFICATION_NO_GO` 只能进入 remediation／重新资格。
- 暗发布前后 Web launcher、API capability 与 runtime gate 都保持关闭。canary 结束后无论结果都恢复关闭；永久公开启用只能由管理员在重新检查证据 freshness 后显式执行。
