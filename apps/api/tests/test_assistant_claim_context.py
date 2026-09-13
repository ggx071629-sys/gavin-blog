from __future__ import annotations

from dataclasses import replace

from app.assistant.hydrate import Evidence
from app.assistant.output import validate_model_answer
from app.assistant.providers import ModelAnswer


def check(
    source,
    answer,
    *,
    quote=None,
    extra=None,
    both=False,
    question=None,
    source_type="project",
    extra_type=None,
):
    first = Evidence(
        "c1", "first", "项目说明", "", "/projects/demo", source, source_type, 1, "v1", 1, ("fts",)
    )
    items = [first]
    supports = [{"citation_id": "c1", "quote": quote or source}]
    if extra:
        items.append(
            replace(
                first,
                alias="c2",
                chunk_id="second",
                body=extra,
                source_type=extra_type or source_type,
            )
        )
        if both:
            supports.append({"citation_id": "c2", "quote": extra})
    parsed = ModelAnswer.model_validate(
        {
            "blocks": [
                {
                    "text": answer,
                    "citation_ids": [s["citation_id"] for s in supports],
                    "supports": supports,
                }
            ]
        }
    )
    kwargs = {"question": question} if question is not None else {}
    return validate_model_answer(parsed, items, finish_reason="stop", **kwargs)


def test_ordinary_claims_preserve_subject_negation_time_and_scope():
    for source, answer in [
        ("项目使用SQLite。", "项目支持自动驾驶。"),
        ("系统不支持离线运行。", "系统支持离线运行。"),
        ("系统过去支持离线运行。", "系统现在支持离线运行。"),
        ("Gavin开发博客。", "Gavin曾登陆月球。"),
        ("测试覆盖登录功能。", "测试覆盖全部功能。"),
        ("Offline mode is not supported.", "Offline mode is supported."),
        ("Alice maintains the API; Bob maintains the client.", "Bob maintains the API."),
        ("只有管理员可以删除文章。", "用户可以删除文章。"),
    ]:
        assert check(source, answer) == "grounding", (source, answer)
        assert not isinstance(check(source, source), str), source
    assert not isinstance(check("项目使用FastAPI和SQLite。", "项目采用FastAPI与SQLite。"), str)
    assert not isinstance(
        check("项目使用FastAPI和SQLite。", "项目采用FastAPI，所给材料未记载获奖情况。"), str
    )


def test_retractions_and_explicit_same_subject_conflicts():
    answer = "About and resume disagree on the stated role; both are self-reports."
    for other, accepted in [
        ("Zebraportfolio self-report: backend engineer.", True),
        ("Anotherperson self-report: backend engineer.", False),
        ("Zebraportfolio self-report: frontend engineer.", False),
        ("This page describes debugging.", False),
    ]:
        result = check(
            "Zebraportfolio self-report: frontend engineer.",
            answer,
            extra=other,
            both=True,
            source_type="about",
            extra_type="resume",
        )
        assert (not isinstance(result, str)) is accepted
    for subject in ("作者", "Gavin", "李明"):
        claim = f"{subject}获得了图灵奖。"
        source = claim + "上述说法不实。"
        assert check(source, claim, quote=claim) == "grounding"
        assert not isinstance(check(source, source), str)
    assert (
        check("项目仅采用MIT许可证。", "项目仅采用MIT许可证。", extra="项目仅采用Apache许可证。")
        == "grounding"
    )
    assert (
        check(
            "项目仅采用MIT许可证。项目仅采用Apache许可证。",
            "项目仅采用MIT许可证。",
            quote="项目仅采用MIT许可证。",
        )
        == "grounding"
    )
    assert (
        check(
            "项目仅采用MIT许可证。",
            "项目仅采用MIT许可证。",
            extra="项目已取消MIT许可证，当前采用Apache许可证。",
        )
        == "grounding"
    )
    assert not isinstance(
        check(
            "甲项目仅采用MIT许可证。", "甲项目仅采用MIT许可证。", extra="乙项目仅采用Apache许可证。"
        ),
        str,
    )
    assert not isinstance(
        check(
            "项目仅采用MIT许可证。",
            "资料存在冲突：项目仅采用MIT许可证；项目仅采用Apache许可证。",
            extra="项目仅采用Apache许可证。",
            both=True,
        ),
        str,
    )
    assert (
        check(
            "项目仅采用MIT许可证。",
            "资料存在冲突：项目仅采用MIT许可证。",
            extra="项目仅采用Apache许可证。",
        )
        == "grounding"
    )


def test_question_topic_and_bounded_missing_information():
    source = "项目使用SQLite。项目采用MIT许可证。"
    assert (
        check(
            source,
            "项目采用MIT许可证。",
            quote="项目采用MIT许可证。",
            question="项目使用什么数据库？",
        )
        == "relevance"
    )
    assert not isinstance(
        check(
            source, "项目使用SQLite。", quote="项目使用SQLite。", question="项目使用什么数据库？"
        ),
        str,
    )
    assert not isinstance(
        check(
            "项目使用SQLite。",
            "项目使用SQLite，所给材料未记载许可证。",
            question="项目使用什么数据库和许可证？",
        ),
        str,
    )
    assert (
        check(
            source,
            "项目使用SQLite，所给材料未记载许可证。",
            question="项目使用什么数据库和许可证？",
        )
        == "grounding"
    )
