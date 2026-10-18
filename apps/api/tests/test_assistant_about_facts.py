from app.assistant.hydrate import Evidence
from app.assistant.output import ValidatedAnswer, validate_model_answer
from app.assistant.prompt import build_prompt
from app.assistant.providers import AnswerBlock, ModelAnswer


def test_about_self_report_prompt_and_bound_citations():
    evidence = Evidence(
        alias="c1", chunk_id="about-chunk", title="关于 Gavin", heading_path="能力自述",
        public_path="/about", body="我从事后端工程。", source_type="about", source_id=1,
        source_version="2", generation_id=1, sources=("fts",),
    )
    prompt = build_prompt(
        question="Gavin 的工作方向是什么？", evidence=[evidence], history=[], provider=object(),
        max_input_tokens=20000, max_output_tokens=1000, context_window_tokens=22000,
    )
    assert prompt is not None
    policy = prompt.messages[0][1]
    assert "published About page" in policy
    assert "self-reported facts, not proof of mastery" in policy
    assert "state the disagreement and cite both sources" in policy
    assert "Article topics, tags and categories cannot establish personal skills" in policy
    answer = ModelAnswer(blocks=[AnswerBlock(text="关于页自述从事后端工程。", citation_ids=["c1"],
        supports=[{"citation_id": "c1", "quote": evidence.body}])])
    valid = validate_model_answer(answer, [evidence], finish_reason="stop")
    assert isinstance(valid, ValidatedAnswer)
    assert valid.citations[0]["path"] == "/about"
    assert valid.citations[0]["title"] == "关于 Gavin"
    bad = ModelAnswer(blocks=[AnswerBlock(text="无依据的说法。", citation_ids=["invented"])])
    assert validate_model_answer(bad, [evidence], finish_reason="stop") == "citation"
