"""Exact, in-place normalization of bounded quantity expressions.

Subject, property, time qualifiers and comparison operators remain in the text.
This module does not infer calendar conversions or arbitrary arithmetic.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, localcontext

NUMERAL = (
    r"[-+]?(?:\d+(?:\.\d+)?|"
    r"[零〇一二两三四五六七八九十百千万亿]+(?:点[零〇一二三四五六七八九]+)?)"
)
UNIT = (
    r"milliseconds?\b|seconds?\b|minutes?\b|hours?\b|"
    r"years?\b|months?\b|days?\b|projects?\b|articles?\b|"
    r"毫秒|分钟|小时|个月|个|项|篇|年|月|天|页|次|秒|%"
)
QUANTITY = re.compile(rf"(?<![A-Za-z0-9_.])({NUMERAL})\s*({UNIT})", re.I)
RANGE = re.compile(
    rf"(?<![A-Za-z0-9_.])({NUMERAL})\s*(?:到|至|[~～–—])\s*({NUMERAL})\s*({UNIT})", re.I
)
RATIO = re.compile(r"((?:比例|占比|成功率|通过率)(?:为|是|[:：])?\s*)(\d+)\s*/\s*(\d+)")
DIGITS = dict(zip("零〇一二两三四五六七八九", (0, 0, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9), strict=True))
MAGNITUDES = {"十": 10, "百": 100, "千": 1000, "万": 10000, "亿": 100000000}
SCALES = {
    "毫秒": ("秒", Decimal("0.001")),
    "millisecond": ("秒", Decimal("0.001")),
    "秒": ("秒", Decimal(1)),
    "second": ("秒", Decimal(1)),
    "分钟": ("秒", Decimal(60)),
    "minute": ("秒", Decimal(60)),
    "小时": ("秒", Decimal(3600)),
    "hour": ("秒", Decimal(3600)),
}
ALIASES = {"year": "年", "month": "个月", "day": "天", "project": "个", "article": "篇"}


def number(value: str) -> Decimal:
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        return Decimal(value)
    sign = -1 if value.startswith("-") else 1
    value = value.lstrip("+-")
    integer, _, fraction = value.partition("点")
    if all(char in DIGITS for char in integer):
        total = int("".join(str(DIGITS[char]) for char in integer))
    else:
        total = section = current = 0
        for char in integer:
            if char in DIGITS:
                current = DIGITS[char]
            else:
                magnitude = MAGNITUDES[char]
                if magnitude < 10000:
                    section += (current or 1) * magnitude
                elif magnitude > total and total:
                    total = (total + section + current) * magnitude
                    section = 0
                else:
                    total += (section + current) * magnitude
                    section = 0
                current = 0
        total += section + current
    result = Decimal(total)
    if fraction:
        result += Decimal("0." + "".join(str(DIGITS[char]) for char in fraction))
    return sign * result


def decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def invalid_quantity(text: str) -> bool:
    return any(int(match[3]) == 0 for match in RATIO.finditer(text))


def canonical_quantities(text: str) -> str:
    # Preserve all input digits; the process default Decimal precision must not
    # round distinct large quantities into the same supported value.
    with localcontext() as context:
        context.prec = max(50, len(text) * 2 + 16)
        return _canonical_quantities(text)


def _canonical_quantities(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(rf"百分之({NUMERAL})", lambda m: decimal_text(number(m[1])) + "%", text)

    def ratio(match):
        denominator = Decimal(match[3])
        if not denominator:
            return match[0]
        numerator = Decimal(match[2]) * 100
        # Only finite decimal equivalents; do not equate rounded thirds.
        denominator_int = int(denominator)
        for prime in (2, 5):
            while denominator_int % prime == 0:
                denominator_int //= prime
        if denominator_int != 1:
            return match[0]
        return match[1] + decimal_text(numerator / denominator) + "%"

    text = RATIO.sub(ratio, text)
    text = RANGE.sub(lambda m: f"{m[1]}{m[3]}至{m[2]}{m[3]}", text)

    def quantity(match):
        value, unit = number(match[1]), match[2].casefold()
        unit = unit.removesuffix("s") if unit.isascii() else unit
        canonical, scale = SCALES.get(unit, (ALIASES.get(unit, unit), Decimal(1)))
        return decimal_text(value * scale) + canonical

    return QUANTITY.sub(quantity, text)
