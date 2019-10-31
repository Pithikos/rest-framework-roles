# from unittest.mock import patch

# import pytest
# from django.test.utils import override_settings

from ..roles import is_admin, is_user, is_anon
from ..parsing import create_lookup, parse_roles, parse_permissions
from ..decorators import expensive, cheap


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
    permissions = [{
        'view': 'myclassview',
        'permissions': {
            'admin': {
                'myaction1': True,
                'myaction2': True,
                'myaction3': True,
            },
            'user': {
                'myaction3': False,
            }
        },
    }]
    # Namely extend views to point to the actual views of the classes if
    # needed
    parsed = parse_permissions(permissions)
    assert parsed == [
        {
            'view': 'myclassview.myaction1',
            'permissions': {'admin': True}
        },
        {
            'view': 'myclassview.myaction2',
            'permissions': {'admin': True}
        },
        {
            'view': 'myclassview.myaction3',
            'permissions': {'admin': True, 'user': False},
        }
    ]

def test_parse_function_views():
    assert parse_permissions([{
        'view': 'myfunctionview',
        'permissions': {'admin': True}
    }]) == [{
        'view': 'myfunctionview',
        'permissions': {'admin': True},
    }]


def test_create_lookup():
    is_not_updating_permissions = lambda v, r: True
    is_self = lambda v, r: True

    roles = {
        'admin': is_admin,
        'user': is_user,
        'anon': is_anon,
    }

    permissions = [{
      'view': 'authentication.views.UserViewSet',
      'permissions': {
        'admin': {
          'create': True,
          'retrieve': True,
          'update': True,
          'partial_update': True,
          'me': True,
        },
        'user': {
          'update': True,
          'partial_update': is_not_updating_permissions,
          'retrieve': is_self,
          'me': True,
        },
        'anon': {
          'create': False,
        }
      }
    }]

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
    outcome = create_lookup(roles, permissions)
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

    permissions = [
        {
          'view': 'authentication.views.UserViewSet',
          'permissions': {
            'admin': {'create': True},
            'expensivo': {'create': True},
            'cheapo': {'create': True},
          }
        }
    ]

    lookup = create_lookup(roles, permissions)
    assert lookup == {
        'authentication.views.UserViewSet.create': [
            (True, is_cheapo), (True, is_admin), (True, is_expensivo)
        ]
    }

# @mock.patch('authentication.models.USER_PAYPLANS', USER_PAYPLANS)
# @mock.patch('authentication.models.USER_PERMISSIONS_SCHEMA', USER_PERMISSIONS_SCHEMA)
# def test_parsing():
    # permissions = [
    #     {
    #         'model': 'fileshare.models.User',
    #         'permissions': [
    #             {
    #                 'role': 'owner',
    #                 '__all__': True,
    #             },
    #             {
    #                 'role': 'anonymous',
    #                 'create': True,
    #                 'customaction': True,
    #             },
    #             {
    #                 'role': 'user',
    #                 'list': True,
    #                 'retrieve': True,
    #             }
    #         ],
    #     }
    # ]
    # expected = {
    #     'authentication.models.User': {
    #         'owner': {
    #             '__all__': True,
    #         },
    #         'anon': {
    #             'list': False,
    #             'retrieve': False,
    #             'create': True,
    #             'partial_update': False,
    #             'update': False,
    #             'destroy': False,
    #             'customaction': True,
    #         },
    #         'user': {
    #             'list': True,
    #             'retrieve': True,
    #             'create': False,
    #             'partial_update': False,
    #             'update': False,
    #             'destroy': False,
    #         },
    # }
