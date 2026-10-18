from app.markdown_media import missing_image_alt_location


def test_missing_image_alt_location_only_flags_blank_image_alts() -> None:
    assert missing_image_alt_location("[普通链接](https://example.com)") is None
    assert missing_image_alt_location("![架构图](/media/1.webp)") is None
    assert missing_image_alt_location("标题\n\n![](/media/1.webp)") == (3, 1)
    assert missing_image_alt_location("前缀 ![   ](/media/1.webp)") == (1, 4)
