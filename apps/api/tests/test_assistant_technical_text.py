from .test_assistant_claim_context import check


def test_grounded_technical_text_preserves_output_guards():
    for text in (
        "条件是 x < 10。", "条件是 x > 0。", "访问数组 a[1]。",
        "访问数组 items [ 1 ][2]。", "类型为 List<T>。", "类型为 Map<K, V>。",
    ):
        assert not isinstance(check(text, text), str), text
    assert check("访问数组 a[1]。", "访问数组 a[2]。") == "grounding"
    assert check("a[99]", "a[99]").text == "`a[99]`[1]"
    for text in (
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
        "<!-- unsafe markup -->", "[link](https://evil.example)",
        "![image](https://evil.example/a.png)", "javascript:alert(1)",
        "这是手写引用。[1]", "Box<svg onload=alert(1)>",
    ):
        assert check(text, text) == "structure", text
