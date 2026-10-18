---
id: decision-local-probe-recovery
level: L2
summary: 本机兼容性证据与累计费用授权分离及保守恢复
load_when:
  - local-probe-recovery
author: Codex
---
# 本机复验与恢复

范围仅development；生产资格、在线预算账本和运行时熔断不变。

v2 probe签名绑定兼容性摘要：模型、endpoint/Key指纹、token/context/timeout及输出schema/协议。价格和日预算独立本地校验；readiness继续绑定当前费用配置，变化后本地重签。上调日预算需明确授权并离线rebind-costs，不产生Chat调用。原探测时间不变，保留先前证据。

v1没有可逆的兼容性字段，转换必须先用原配置校验旧混合摘要；原文件保留，新文件嵌入旧签名payload及字节摘要。不能从最近正常回答推断资格通过。原配置丢失时留待明确授权的重新探测。

v3 ledger在同一路径保存旧文本和摘要、授权列表、全部attempt及追加恢复记录，使用原readiness密钥签名。唯一授权ID绑定当前配置与明确的累计次数/金额、日预算上限；跨授权累计消耗永不清零。新ID不天然增加余额，相同ID不能修改或复活。ledger签名异常和未知schema拒绝，不支持自动密钥迁移。

sending、unknown、measured_fail均阻断；静止确认与故障调查后追加恢复事实，不重写attempt或退还费用/次数。sending和unknown按reservation与settled较大者计入，已测失败保留settled。新授权也不能跳过未恢复失败。额度耗尽需明确新增累计上限，不由每日runtime预算提供探测额度。

完整探测、授权、恢复共用run lock；签名写入用原子替换。进程崩溃保留sending，恢复必须确认进程退出，晚到settlement不能覆盖恢复事实。新授权的探测使用新output，不覆盖旧成功/失败证据。用启动环境GAVIN_ASSISTANT_LOCAL_PROBE_PATH选择新文件。

这是应用内可审计的操作者授权合同，不是供应商总账或外部不可修改审计系统。持有本机签名密钥及写权限的操作者仍能修改代码；不声称防御已完全控制主机的人。实施验证仅使用临时账本与模型替身，未改变真实费用授权。
