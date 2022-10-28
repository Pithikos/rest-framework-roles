import pytest

from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.parsing import parse_roles, parse_view_permissions, get_permission_list
from rest_framework_roles.decorators import role_checker
from rest_framework_roles.granting import allof, anyof


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
    @role_checker(cost=50)
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
        'create': {
            'admin': True,
            'anon': False,
        },
        'retrieve': {
            'admin': True,
            'user': is_self,
        },
        'update': {
            'admin': True,
            'user': True,
        },
        'partial_update': {
            'admin': True,
            'user': is_not_updating_permissions,
        },
        'me': {
            'admin': True,
            'user': True,
        },
    }

    expected = {
        'create': (
            (True, is_admin),
            (False, is_anon),
        ),
        'retrieve': (
            (True, is_admin),
            (is_self, is_user),
        ),
        'update': (
            (True, is_admin),
            (True, is_user),
        ),
        'partial_update': (
            (True, is_admin),
            (is_not_updating_permissions, is_user),
        ),
        'me': (
            (True, is_admin),
            (True, is_user),
        )
    }
    outcome = parse_view_permissions(view_permissions, roles)
    assert outcome == expected


def test_rules_sorted_by_cost():

    @role_checker(cose=5)
    def is_expensivo(*args):
        pass

    @role_checker(cost=-5)
    def is_cheapo(*args):
        pass

    roles = {
        'admin': is_admin,
        'cheapo': is_cheapo,
        'expensivo': is_expensivo,
    }

    permissions = {
      'create': {
        'admin': True,
        'expensivo': True,
        'cheapo': True,
      }
    }

    lookup = parse_view_permissions(permissions, roles)
    assert lookup == {
        'create': (
            (True, is_cheapo), (True, is_admin), (True, is_expensivo)
        )
    }


@pytest.mark.parametrize("samehash,p1,p2", (
    (True, ((True, is_user), (True, is_admin)), ((True, is_user), (True, is_admin))),
    (False, ((True, is_user), (True, is_admin)), ((True, is_user), (True, is_anon))),
))
def test_hashing_permission_tuples(samehash, p1, p2):
    if samehash:
        assert hash(p1) == hash(p2)
    else:
        assert hash(p1) != hash(p2)


@pytest.mark.parametrize("samehash,p1,p2", (
    (True, anyof(True, True), anyof(True, True)),
    (False, anyof(True, True), anyof(True, False)),
    (False, allof(True, True), anyof(True, True)),
    (True, anyof(is_admin, is_user), anyof(is_admin, is_user)),
    (False, anyof(is_admin, is_user), anyof(is_user, is_admin)),  # order matters
))
def test_hashing_permission_helpers(samehash, p1, p2):
    if samehash:
        assert hash(p1) == hash(p2)
    else:
        assert hash(p1) != hash(p2)


@pytest.mark.parametrize("samehash,p1,p2", (
    (True, {"admin": True}, {"admin": True}),
    (False, {"admin": True}, {"admin": False}),
    (False, {"admin": True}, {"user": True}),
    (True, {"admin": anyof(True)}, {"admin": anyof(True)}),
))
def test_hashing_permissions(samehash, p1, p2):
    roles = parse_roles({
        "admin": is_admin,
        "user": is_user,
        "anon": is_anon,
    })
    perm1 = tuple(get_permission_list(roles, p1))
    perm2 = tuple(get_permission_list(roles, p2))
    if samehash:
        assert hash(perm1) == hash(perm2)
    else:
        assert hash(perm1) != hash(perm2)