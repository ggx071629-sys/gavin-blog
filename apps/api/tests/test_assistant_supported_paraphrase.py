from .test_assistant_claim_context import check


def test_supported_technical_paraphrases_and_explicit_enumeration_counts():
    for source, answer in [
        ("作者使用Python开发项目。", "作者用Python开发项目。"),
        ("项目依赖SQLite。", "项目依赖 SQLite 数据库。"),
        ("操作耗时60秒。", "操作耗时1分钟。"),
        ("项目包括甲、乙、丙三个模块。", "项目包括3个模块。"),
        ("项目包括鉴权、日志两个模块。", "项目包括2个模块。"),
        ("服务会在失败后再试一次。", "服务失败后会重试一次。"),
    ]:
        assert not isinstance(check(source, answer), str), (source, answer)
    for source, answer in [
        ("项目依赖SQLite。", "项目依赖 PostgreSQL 数据库。"),
        ("项目包括甲、乙、丙三个模块。", "项目包括4个模块。"),
        ("项目包括甲、乙等模块。", "项目包括2个模块。"),
        ("项目包括甲、甲、乙三个模块。", "项目包括3个模块。"),
        ("项目包括甲、乙、丙四个模块。", "项目包括4个模块。"),
        ("服务会在失败后再试一次。", "服务失败后会一直重试。"),
    ]:
        assert check(source, answer) == "grounding", (source, answer)
