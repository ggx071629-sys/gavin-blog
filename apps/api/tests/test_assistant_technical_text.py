import pytest

from .test_assistant_claim_context import check


def test_grounded_technical_text_preserves_output_guards():
    for text in (
        "条件是 x < 10。",
        "条件是 x > 0。",
        "访问数组 a[1]。",
        "访问数组 `items [ 1 ][2]`。",
        "类型为 List<T>。",
        "类型为 Map<K, V>。",
    ):
        assert not isinstance(check(text, text), str), text
    assert check("访问数组 a[1]。", "访问数组 a[2]。") == "grounding"
    assert check("a[99]", "a[99]").text == "`a[99]`[1]"
    for text in (
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<!-- unsafe markup -->",
        "[link](https://evil.example)",
        "![image](https://evil.example/a.png)",
        "javascript:alert(1)",
        "这是手写引用。[1]",
        "Box<svg onload=alert(1)>",
    ):
        assert check(text, text) == "structure", text


@pytest.mark.parametrize(
    "text",
    [
        "See [1] in the corpus",
        "See\t[1] in the corpus",
        "See\n[1] in the corpus",
        "Source [12]",
        "Sources [1][2]",
        "访问数组 items [1]。",
        "`a[1]` See [2]",
        "`[1]`",
        "`items [1]",
        "items [1]`",
        r"\`See [1]\`",
        "See\r[1]",
        "See\u00a0[1]",
    ],
)
def test_reserved_markers_in_prose_rejected_even_when_grounded(text):
    assert check(text, text) == "structure"


@pytest.mark.parametrize(
    "text,rendered",
    [
        ("a[1]", "`a[1]`[1]"),
        ("items[ 1 ][2]", "`items[ 1 ][2]`[1]"),
        ("`items [1]`", "`items [1]`[1]"),
        ("`items\t[1][2]`", "`items\t[1][2]`[1]"),
        ("访问数组 `items [ 1 ][2]`。", "访问数组 `items [ 1 ][2]`。[1]"),
    ],
)
def test_array_syntax_preserves_generated_citation(text, rendered):
    result = check(text, text)
    assert not isinstance(result, str)
    assert result.text == rendered


@pytest.mark.parametrize(
    "text",
    [
        "`a[1] <script>alert(1)</script>`",
        "`a[1] [link](https://evil.example)`",
    ],
)
def test_array_code_does_not_exempt_unsafe_markup(text):
    assert check(text, text) == "structure"
