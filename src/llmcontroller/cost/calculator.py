from llmcontroller.cost.pricing import PRICING


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost in USD, rounded to 8 decimal places."""
    if model not in PRICING:
        raise ValueError(f"Unknown model: {model}")
    pricing = PRICING[model]
    input_cost = (input_tokens / 1000) * pricing["input_per_1k"]
    output_cost = (output_tokens / 1000) * pricing["output_per_1k"]
    return round(input_cost + output_cost, 8)
