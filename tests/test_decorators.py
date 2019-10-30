import pytest

from ..decorators import expensive, cheap, DEFAULT_EXPENSIVE, DEFAULT_CHEAP


def test_decorating_with_default_cost():
    @expensive
    def is_owner():
        pass
    @cheap
    def is_cheapo():
        pass
    assert is_owner.cost == DEFAULT_EXPENSIVE
    assert is_cheapo.cost == DEFAULT_CHEAP


def test_decorating_with_explicit_cost():
    expensive_cost = DEFAULT_EXPENSIVE + 10
    cheap_cost = DEFAULT_CHEAP + 10
    @expensive(cost=expensive_cost)
    def is_owner():
        pass
    @cheap(cost=cheap_cost)
    def is_cheapo():
        pass
        # assert
    assert is_owner.cost == expensive_cost
    assert is_cheapo.cost == cheap_cost


def test_invalid_cost_values():
    with pytest.raises(AssertionError):
        @expensive(cost=DEFAULT_EXPENSIVE-1)
        def is_cheapo():
            pass
