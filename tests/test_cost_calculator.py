import pytest

from llmcontroller.cost.calculator import calculate_cost


def test_known_model_cost():
    assert calculate_cost("claude-3-sonnet", 1000, 1000) == pytest.approx(0.018)


def test_zero_tokens_is_zero():
    assert calculate_cost("claude-3-sonnet", 0, 0) == 0.0


def test_unknown_model_raises():
    with pytest.raises(ValueError):
        calculate_cost("does-not-exist", 10, 10)
