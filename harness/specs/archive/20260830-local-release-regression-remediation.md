---
id: archive-20260830-local-release-regression-remediation
level: L2
summary: 修复内容写 fence 并发回归、质量门禁收尾与服务端构建目标漂移，恢复可重复的本地发布候选
load_when:
  - task:20260830-local-release-regression-remediation
author: Gavin
task_id: 20260830-local-release-regression-remediation
status: compressed
documentation_impact: required
documentation_targets:
  - README.md
  - apps/api/README.md
  - apps/web/README.md
documentation_reason: 本任务修正项目状态、内容写 fence 与 E2E 隔离运行语义，必须同步公开项目状态及 API／Web 边界。
state_history:
---

# 20260830-local-release-regression-remediation

Deterministic compressed record. The original active spec remains in Git history.

## Goal

恢复一份不依赖任何真实部署的可重复本地发布候选：单 API owner 内的正常并发内容 mutation 必须有界串行且保持既有成功合同，外部备份／恢复 fence 仍立即 fail closed；质量门禁保留现有受监督生命周期，并在具备本地子进程管理权限的验证上下文中正常回收服务；Nitro 服务端构建目标与受支持的 Node 22／BigInt 能力一致；项目状态文档与权威 Spec 索引一致；最终完整 release gate 从干净工作树通过并正常退出。

## Acceptance criteria

- AC-1: 应用为每个 API 实例建立进程内 async 内容写序列化边界；同一实例中的并发认证内容 mutation 在没有外部 fence 时均按原合同成功，不因彼此竞争跨进程文件锁返回 503。序列化后每个请求仍单独取得并释放既有跨进程 fence；外部备份／恢复进程持锁时 mutation 继续立即返回稳定 503、`Retry-After: 5` 且不写入数据库。取消、异常和响应完成路径不得遗留进程内或文件锁。
- AC-2: Web 质量门禁保留并发 fixture、原始断言、Playwright WebServer 管理和 Harness 已注册的非零 release stage 超时；在允许当前测试进程终止其自建 Windows 子进程树的本地上下文中，Playwright、Nuxt preview、隔离 API 和浏览器子进程在通过或受控失败后均有界退出且不遗留占用端口的孤儿。受限上下文返回的 `Access denied` 必须被识别为执行环境限制，不能靠删除生命周期管理或放宽门禁绕过。
- AC-3: Nitro 服务端构建明确使用支持 BigInt 的目标并与项目声明的 Node 22 运行基线一致；可信代理 IPv4、IPv4-mapped IPv6、IPv6 和 CIDR 单元测试保持通过，生产构建不再输出 `Big integer literals are not available in ... es2019` 警告。
- AC-4: 根 README 不再把已压缩的 Admin Login 规格描述为当前 active；API README 准确记录普通单 owner mutation 的进程内序列化与外部备份 fence fail-closed 区别。历史已取消、退役或压缩任务不被重新列为待完成。
- AC-5: 当前 HEAD 的 API lint／测试、Harness tests、OpenAPI 一致性、Web 类型／单测／构建／质量／失败态、核心 E2E 与 Harness integrity 均由一次完整 `npm run quality:release` 成功覆盖；命令正常退出、工作树保持干净，local-only change coverage skip 只作为明确记录而不被描述成远端 CI 证据。
- AC-6: E2E 父 runner 从子进程环境中移除主机 `GAVIN_*` 配置，只保留显式允许的测试端口并重新注入本次随机 run root；助手 E2E API 显式声明通过当前校验所需的独立本地测试 secrets、provider 限制和确定性 test providers。助手 Web E2E 运行本地生产 Node preview；Nuxt 助手代理从 H3 的直接 peer 地址解析能力读取客户端 socket 身份，不信任 `X-Forwarded-For`，并在缺少 direct peer 时 fail closed。测试不得读取真实资格、密钥或 provider 身份，也不得发起非 loopback 网络调用。

## Result

Verified and closed by the harness close command.

## Evidence

[20260830-local-release-regression-remediation.json](../../verification/evidence/20260830-local-release-regression-remediation.json)

Closed at 2026-08-30T15:02:09.470844+00:00.
