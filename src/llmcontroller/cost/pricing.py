# USD price per 1,000 tokens. Update when providers change pricing.
PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-3-sonnet": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    "claude-3-opus": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "claude-3-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    # OpenAI
    "gpt-4o": {"input_per_1k": 0.0025, "output_per_1k": 0.01},
    "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
    "gpt-3.5-turbo": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
    # Mistral (approximate)
    "mistral-small-latest": {"input_per_1k": 0.0002, "output_per_1k": 0.0006},
    "mistral-large-latest": {"input_per_1k": 0.002, "output_per_1k": 0.006},
    # Other OpenAI-compatible gateway models (approximate)
    "claude-opus-4-7": {"input_per_1k": 0.015, "output_per_1k": 0.075},
    "gemini-2.5-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.0003},
}
