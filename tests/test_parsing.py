from unittest.mock import patch

import pytest
from django.test.utils import override_settings

from ..roles import *
from ..parsing import create_lookup

# ROLES = {
#     'user': {'role_checker': is_user},
#     'anonymous': {'role_checker': is_anon},
# }
#
# VIEW_PERMISSIONS = [
#     {
#         'model': 'fileshare.models.User',
#         'permissions': {
#             'owner': {
#                 '__all__': True,
#             },
#             'anon': {
#                 'create': True,
#             },
#             'user': {
#                 'list': True,
#                 'retrieve': True,
#             }
#         }
#     }
# ]

@patch('rest_framework_roles.tests.settings.ROLES', [])
@patch('rest_framework_roles.tests.settings.PERMISSIONS', [])
def test_usage():
    pass


def test_transformation():
    is_not_updating_permissions = lambda v, r: True
    is_self = lambda v, r: True

    roles = {
        'anon': is_anon,
        'admin': is_admin,
        'user': is_user,
    }

    permissions = [{
      'view': 'authentication.views.UserViewSet',
      'permissions': {
        'anon': {
          'create': True
        },
        'admin': {
          'list': True,
          'retrieve': True,
          'destroy': True,
          'update': True,
          'partial_update': True,
          'me': True
        },
        'user': {
          'update': True,
          'partial_update': is_not_updating_permissions,
          'retrieve': is_self,
          'me': True
        }
      }
    }]

    expected = {
      'authentication.views.UserViewSet': {
        'create': [
            (is_anon, True)
        ],
        'list': [
            (is_admin, True)
        ],
        'retrieve': [
            (is_admin, True),
            (is_user, is_self),
        ],
        'destroy': [
            (is_admin, True)
        ],
        'update': [
            (is_user, True)
        ],
        'partial_update': [
            (is_admin, True),
            (is_user, is_not_updating_permissions)
        ],
        'me': [
            (is_admin, True),
            (is_user, True),
        ]
      }
    }
    outcome = create_lookup(roles, permissions)
    import IPython; IPython.embed(using=False)
    assert outcome == expected


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
