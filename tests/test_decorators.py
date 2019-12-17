import pytest

from ..decorators import expensive, cheap, DEFAULT_EXPENSIVE, DEFAULT_CHEAP, allowed, disallowed
from ..roles import is_admin


class TestRoleCheckerDecorators:

    def test_decorating_with_default_cost(self):
        @expensive
        def is_owner():
            pass
        @cheap
        def is_cheapo():
            pass
        assert is_owner.cost == DEFAULT_EXPENSIVE
        assert is_cheapo.cost == DEFAULT_CHEAP

    def test_decorating_with_explicit_cost(self):
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

    def test_invalid_cost_values(self):
        with pytest.raises(AssertionError):
            @expensive(cost=DEFAULT_EXPENSIVE-1)
            def is_cheapo():
                pass


class TestViewDecorators:
    def test_attaches_view_permissions_to_view(self):
        @allowed('admin')
        def allowed_admin():
            pass

        @disallowed('admin')
        def disallowed_admin():
            pass

        assert hasattr(allowed_admin, 'view_permissions')
        assert type(allowed_admin.view_permissions) is list
        assert (True, is_admin) in allowed_admin.view_permissions

    def test_invalid_role_raises_exception(self):
        with pytest.raises(Exception):
            @allowed('garbage')
            def myview():
                pass
