# from unittest.mock import patch

# import pytest
# from django.test.utils import override_settings

from ..roles import is_admin, is_user, is_anon
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

# @patch('rest_framework_roles.tests.settings.ROLES', [])
# @patch('rest_framework_roles.tests.settings.PERMISSIONS', [])
# def test_usage():
#     pass


def test_transformation():
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
      'authentication.views.UserViewSet': {
        'create': [
            (True, is_admin),
            (False, is_anon),
        ],
        'retrieve': [
            (True, is_admin),
            (is_self, is_user),
        ],
        'update': [
            (True, is_admin),
            (True, is_user),
        ],
        'partial_update': [
            (True, is_admin),
            (is_not_updating_permissions, is_user),
        ],
        'me': [
            (True, is_admin),
            (True, is_user),
        ]
      }
    }
    outcome = create_lookup(roles, permissions)
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
