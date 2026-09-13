from __future__ import annotations

from decimal import ROUND_UP, Decimal

MICRO_CNY = 1_000_000
ZERO = Decimal("0")


def cny_to_micro(value: Decimal) -> int:
    if value < ZERO:
        raise ValueError("currency values must be non-negative")
    quantized = (value * MICRO_CNY).to_integral_value(rounding=ROUND_UP)
    return int(quantized)


def tokens_cost_micro(tokens: int, price_cny_per_million: Decimal) -> int:
    if tokens < 0:
        raise ValueError("token counts must be non-negative")
    price_micro_per_million = cny_to_micro(price_cny_per_million)
    if tokens == 0 or price_micro_per_million == 0:
        return 0
    return (tokens * price_micro_per_million + MICRO_CNY - 1) // MICRO_CNY


def snapshot_json(*, input_cny_per_million: Decimal, output_cny_per_million: Decimal) -> str:
    return (
        '{"input_cny_per_million":"'
        f"{input_cny_per_million.normalize()}"
        '","output_cny_per_million":"'
        f"{output_cny_per_million.normalize()}"
        '","currency":"CNY"}'
    )
