---
id: decision-assistant-source-ingestion
level: L1
summary: 关于页发布资格和简历显式刷新、版本化引用的用户确认边界
load_when:
  - assistant-sources
  - assistant-resume
  - assistant-about
author: Codex
---
# 问答助手的关于页与简历来源

2026-09-11 用户确认。关于页与简历来源均已实现，隔离夹具分项验收已通过；真实公开PDF的标准管线隔离导入也已通过，随后已完成实际本地内容库接入；公网生产资格不在本轮交付内。

关于页仅管理员主动发布/回滚后的当前修订参与 RAG；默认 seed 排除，草稿不可见。版本资格用显式字段保存，发布与 outbox 同事务，检索及输出复检当前版本，等待新版索引不使用旧片段。引用精确指向 `/about`，显示“关于 Gavin”。个人自述按自述引用，不能由文章主题推断能力；同一事实冲突时引用双方并说明矛盾。

简历的最终更新方式是首次配置/换址自动导入，同址文件更新后管理员“立即刷新”。此前小时级检查方案已撤回，不设置周期检查和时间过期。检查失败暂停简历证据，成功检查后恢复；自动导入不增加人工预览确认。允许后端保存可撤销的版本化 PDF 快照，保留名片原 URL 查看入口，不新增正文网页。

简历复用内容 SQLite 保存绑定代次、版本、PDF 与提取文本，独立于问答 runtime；沿用内容备份。换址/清空撤销访问并清理旧缓存；不承诺删除既有备份或访客已下载文件。可信下载与短生命周期解析子进程受资源限制，不添加常驻服务、OCR、监测、额外聊天留存或付费调用。

细节见[来源契约](../../../plan-build/assistant-upgrade/ASSISTANT-UPGRADE-CONTRACT.md)和[最终参数](../../../plan-build/assistant-upgrade/completed/assistant-upgrade-design/Q1-02.md)。真实文件结果见[Q4-03](../../../plan-build/assistant-upgrade/completed/assistant-upgrade-verification/Q4-03.md)；隔离夹具、真实文件隔离导入和生产资格证据必须区分。
