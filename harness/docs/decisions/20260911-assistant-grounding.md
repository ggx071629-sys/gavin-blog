---
id: decision-assistant-grounding
level: L1
summary: 自然综合按块绑定内部原句并保持离线语义评估边界
load_when:
  - assistant-grounding
author: Codex
---

# 回答支持材料

已确认自然综合与部分回答；普通内容仍可综合，高风险个人奖项、能力、经验年数和现职的事实句保守保留原文主体、否定、时间及归属。事实不足不能发布为有据回答。程序不会通用判断语义蕴含，未覆盖语句仍可能漏检；语义评估先离线，不新增在线模型调用。

每块内部 supports 含 citation_id/quote，最多 8 项，每项 1–1200 字符。引用集合必须与材料别名集合一致，quote 必须是本轮实际送入且当前仍有效的 body 中连续原文；不得借前块、历史、标题或撤销来源补足。原句存在不等于结论成立。固定简历不可用块在后端确认时允许两列表为空。

生产 strict schema 与本地 JSON 协议均携带支持材料。Python 旧结构读取可缺 supports，但输出验证拒绝，不豁免恢复；完成的旧会话不迁移。材料沿既有 attempt.parsed_json 短期暂存，授权终止事务清除；不进入公开/管理响应、SSE、成功历史或 checkpoint。管理端已有来源 excerpt 仍保留，不能与模型生成 supports 混同。

字段与提示计入现有输入估算，生成材料占用原输出 token 上限；没有提高额度或增加重试次数。较小输入预算可能选中更少来源。支持不足沿用 grounding/证据不足；格式、截断、超时、未知结果和最多两次生成沿用既有规则。

验证只用本地函数、固定替身及 Codex 证据对照；不能据此声称真实模型已抗注入或生产就绪。计划与基线见 [阶段一](../../../plan-build/assistant-safety/PHASE-1-BASELINE.md)。
