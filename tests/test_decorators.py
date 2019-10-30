from ..decorators import expensive, cheap, DEFAULT_EXPENSIVE, DEFAULT_CHEAP


def test_decorating_cost_without_call():
    @expensive
    def is_owner():
        pass
    @cheap
    def is_cheapo():
        pass
    assert is_owner.cost == DEFAULT_EXPENSIVE
    assert is_cheapo.cost == DEFAULT_CHEAP
