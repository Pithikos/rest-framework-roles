import pytest

from rest_framework_roles.decorators import role_checker, DEFAULT_COST
from rest_framework_roles.roles import is_admin


class TestRoleCheckerDecorators:

    def test_decorator_without_args(self):
        # Ensure @expensive results to the same as @expensive(cost=60)
        @role_checker(cost=50)
        def decorated1():
            pass
        @role_checker(cost=60)
        def decorated2():
            pass
        assert not decorated1.__name__.startswith('decorator')
        assert decorated1.__name__.startswith('wrapped')
        assert not decorated2.__name__.startswith('decorator')
        assert decorated2.__name__.startswith('wrapped')
        assert decorated1.__qualname__ == decorated2.__qualname__

    def test_decorating_with_default_cost(self):
        @role_checker(cost=50)
        def is_owner():
            pass
        @role_checker
        def is_cheapo():
            pass
        assert is_owner.cost == 50
        assert is_cheapo.cost == DEFAULT_COST

    def test_decorating_with_explicit_cost(self):
        expensive_cost = DEFAULT_COST + 10
        cheap_cost = DEFAULT_COST + 1
        @role_checker(cost=expensive_cost)
        def is_owner():
            pass
        @role_checker(cost=cheap_cost)
        def is_cheapo():
            pass
            # assert
        assert is_owner.cost == expensive_cost
        assert is_cheapo.cost == cheap_cost