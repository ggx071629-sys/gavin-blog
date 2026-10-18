from .test_assistant_claim_context import check


def test_complete_single_line_code_presentation_preserves_all_facts():
    source = "执行：  \n```bash\nwidget check --dry-run\n```"
    assert not isinstance(check(source, "执行：`widget check --dry-run`。"), str)
    assert not isinstance(check("查看：\n~~~sh\nwidget status\n~~~", "查看：widget status。"), str)
    for answer in [
        "执行：`widget check`。", "执行：`widget check --force`。",
        "禁止执行：`widget check --dry-run`。", "执行：`widgetcheck --dry-run`。",
    ]:
        assert check(source, answer) == "grounding"
    for prefix in ["不要执行：", "仅测试环境执行：", "管理员执行："]:
        qualified = prefix + "\n```sh\nwidget reset\n```"
        assert check(qualified, "执行：`widget reset`。") == "grounding"
        assert not isinstance(check(qualified, prefix + "`widget reset`。"), str)


def test_code_presentation_cannot_repair_quotes_or_drop_retractions():
    source = "执行：\n```sh\nwidget check\n```\n上述说法错误。"
    assert check(source, "执行：`widget check`。", quote=source.split("\n上述")[0]) == "grounding"
    # Exact raw quotation remains mandatory even if the displayed text is equivalent.
    raw = "执行：\n```sh\nwidget check\n```"
    assert check(raw, "执行：`widget check`。", quote="执行：`widget check`") == "grounding"
    for source, answer in [
        ("执行：\n```sh\nwidget a\nwidget b\n```", "执行：`widget a widget b`。"),
        ("执行：`echo `value``", "执行：`echo value`。"),
        ("执行：~~widget reset~~", "执行：widget reset。"),
        ("执行：`widget check`，但仅限测试。", "执行：`widget check`。"),
        ("执行：`echo 'a  b'`", "执行：`echo 'a b'`。"),
        ("执行：`widget file。`", "执行：`widget file`。"),
    ]:
        assert check(source, answer) == "grounding"
