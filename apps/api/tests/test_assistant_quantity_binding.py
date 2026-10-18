from .test_assistant_claim_context import check


def test_quantities_preserve_binding_and_allow_exact_conversions():
    for source, answer in [
        ("系统重试三次。", "系统重试3次。"),
        ("操作耗时60秒。", "操作耗时1分钟。"),
        ("操作耗时0.1秒。", "操作耗时100毫秒。"),
        ("A方案耗时60秒，B方案耗时120秒。", "A方案耗时1分钟，B方案耗时2分钟。"),
        ("范围为1到2分钟。", "范围为60至120秒。"),
        ("成功率为百分之五十。", "成功率为50%。"),
        ("成功率为1/2。", "成功率为50%。"),
        ("至少需要十二个副本。", "至少需要12个副本。"),
        ("Duration is 60 seconds.", "Duration is 1 minute."),
    ]:
        assert not isinstance(check(source, answer), str), (source, answer)
    for source, answer in [
        ("A方案耗时10秒，B方案耗时20秒。", "A方案耗时20秒，B方案耗时10秒。"),
        ("系统重试三次。", "系统重试八次。"),
        ("至少需要十二个副本。", "最多需要12个副本。"),
        ("2025年最多重试3次。", "2026年最多重试3次。"),
        ("成功率为1/2。", "成功率为1/3。"),
        ("成功率为1/2。", "成功率为1/0。"),
        ("范围为1到2分钟。", "范围为60至180秒。"),
        ("计划需要1个月。", "计划需要30天。"),
        ("耗时123456789012345678901234567890秒。", "耗时123456789012345678901234567891秒。"),
    ]:
        assert check(source, answer) == "grounding", (source, answer)
