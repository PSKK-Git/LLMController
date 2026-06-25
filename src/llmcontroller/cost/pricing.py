# USD price per 1,000 tokens. Update when providers change pricing.
PRICING: dict[str, dict[str, float]] = {
    "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
}
