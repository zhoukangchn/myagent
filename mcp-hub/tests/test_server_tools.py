import pytest

from server.main import calculate


def test_calculate_operations() -> None:
    assert calculate("add", 2, 3) == 5
    assert calculate("subtract", 5, 2) == 3
    assert calculate("multiply", 4, 3) == 12
    assert calculate("divide", 8, 2) == 4


def test_calculate_divide_by_zero() -> None:
    with pytest.raises(ValueError):
        calculate("divide", 5, 0)


def test_calculate_invalid_operation() -> None:
    with pytest.raises(ValueError):
        calculate("mod", 5, 2)
