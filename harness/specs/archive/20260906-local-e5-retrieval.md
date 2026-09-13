---
id: archive-20260906-local-e5-retrieval
level: L2
summary: 在 Windows 开发机接入固定 E5 CPU 服务和双语检索，保持生产关闭
load_when:
  - task:20260906-local-e5-retrieval
task_id: 20260906-local-e5-retrieval
status: compressed
documentation_impact: required
documentation_targets:
  - apps/api/README.md
  - harness/docs/architecture/boundaries.md
  - harness/docs/decisions/20260906-local-e5-retrieval.md
documentation_reason: 新增独立模型进程、固定制品、token 切片及真实本地检索操作，需明确身份、资源和运维边界。
evidence_sha256: 009b4c2bad1c816747a0a4d8a680ef8f4796cb518323fb915d76183f3ef1cacb
state_history:
---

# 20260906-local-e5-retrieval

Deterministic compressed record. The original active spec remains in Git history.

## Goal

交付由 apps/api 所有的独立、单 CPU 模型进程和可复现下载工具；API/Worker 仅加载 tokenizer，共享内部鉴权模型服务。完成 query/passage 分流、384/64 token 切片、真实本地索引/检索运行入口及验证记录。使用现有 staging/outbox/fence/finalize，始终不自动启用在线问答。

## Acceptance criteria

- AC-1: 模型制品固定官方完整 revision 和逐文件 SHA-256；独立锁定 CPU 推理依赖，本地缺失或哈希/身份不符启动失败，离线重启不下载。模型服务单 owner、线程 1、批次 1、并发 1、有限优先队列与有界等待；停机拒绝新请求并完成在途推理。
- AC-2: 内部鉴权 /v1/embeddings 返回有序 384 维有限归一化向量和真实含特殊 token 的 usage，支持 float/base64；拒绝错误模型/维度/批次、无前缀、空白及超过 512 tokens 输入。公开健康仅报告存活，鉴权 readiness 返回固定身份，不泄露秘密。
- AC-3: 仅 E5 适配给 query/passages 添加一次角色前缀并核验服务身份；固定 tokenizer 对正文按 384 tokens、重叠 64 切片，最终含前缀/特殊 token 不超 512，保留源版本/标题定位；完整当前问题优先，历史仅占剩余 token，当前问题超长通过既有 dense_skipped/lexical degraded 路径而非截断或收费失败。pipeline 与模型版本绑定新 generation，其他 provider 保持行为。
- AC-4: 显式本地真实检索入口不需要 Chat，要求独立认证 Qdrant，复用 Worker staging/finalize 安全流程，保留离线演示命令；可运行 smoke、检索与本机测量，文档准确列出实测和未完成阶段，生产默认关闭。

## Result

Verified and closed by the harness close command.

## Evidence

[20260906-local-e5-retrieval.json](../../verification/evidence/20260906-local-e5-retrieval.json)

SHA-256: `009b4c2bad1c816747a0a4d8a680ef8f4796cb518323fb915d76183f3ef1cacb`

Closed at 2026-09-06T09:44:09.944091+00:00.
