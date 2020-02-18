from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.parsing import parse_roles, parse_view_permissions
from rest_framework_roles.decorators import expensive, cheap


def test_parse_roles():
    # No cost
    assert parse_roles({'admin': is_admin}) == {
        'admin': {
            'role_name': 'admin',
            'role_checker': is_admin,
            'role_checker_cost': 0,
        }
    }


def test_parse_roles_adds_cost_attr():
    roles = parse_roles({'admin': is_admin})
    assert hasattr(roles['admin']['role_checker'], 'cost')
    assert roles['admin']['role_checker'].cost == roles['admin']['role_checker_cost']


def test_parse_roles_cost():
    @expensive(cost=50)
    def is_owner():
        pass

    parsed = parse_roles({'owner': is_owner})
    assert parsed == {
        'owner': {
            'role_name': 'owner',
            'role_checker': is_owner,
            'role_checker_cost': 50,
        }
    }


def test_parse_view_permissions():
    is_not_updating_permissions = lambda v, r: True
    is_self = lambda v, r: True

    roles = {
        'admin': is_admin,
        'user': is_user,
        'anon': is_anon,
    }

    view_permissions = {
        'authentication.views.UserViewSet.create': {
            'admin': True,
            'anon': False,
        },
        'authentication.views.UserViewSet.retrieve': {
            'admin': True,
            'user': is_self,
        },
        'authentication.views.UserViewSet.update': {
            'admin': True,
            'user': True,
        },
        'authentication.views.UserViewSet.partial_update': {
            'admin': True,
            'user': is_not_updating_permissions,
        },
        'authentication.views.UserViewSet.me': {
            'admin': True,
            'user': True,
        },
    }

    expected = {
        'authentication.views.UserViewSet.create': [
            (True, is_admin),
            (False, is_anon),
        ],
        'authentication.views.UserViewSet.retrieve': [
            (True, is_admin),
            (is_self, is_user),
        ],
        'authentication.views.UserViewSet.update': [
            (True, is_admin),
            (True, is_user),
        ],
        'authentication.views.UserViewSet.partial_update': [
            (True, is_admin),
            (is_not_updating_permissions, is_user),
        ],
        'authentication.views.UserViewSet.me': [
            (True, is_admin),
            (True, is_user),
        ]
    }
    outcome = parse_view_permissions(view_permissions, roles)
    assert outcome == expected


def test_rules_sorted_by_cost():

    @expensive
    def is_expensivo(*args):
        pass

    @cheap(cost=-5)
    def is_cheapo(*args):
        pass

    roles = {
        'admin': is_admin,
        'cheapo': is_cheapo,
        'expensivo': is_expensivo,
    }

    permissions = {
      'authentication.views.UserViewSet.create': {
        'admin': True,
        'expensivo': True,
        'cheapo': True,
      }
    }

    lookup = parse_view_permissions(permissions, roles)
    assert lookup == {
        'authentication.views.UserViewSet.create': [
            (True, is_cheapo), (True, is_admin), (True, is_expensivo)
        ]
    }
