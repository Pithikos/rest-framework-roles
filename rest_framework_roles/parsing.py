"""
PREPARSED

view_settings can be part of the body in a class or as a global setting. The
only difference is that in the latter, you need to specify full module paths.


settings style:
{
    'myapp.views.MyModel.myview': {
        'admin': True,
        'user': False,
    }
}

class-based view_settings:
{
    'myview': {
        'admin': True,
        'user': False,
    }
}

POSTPARSED

In all cases we get a lookup table where the permissions have been converted
to a permission list. For this the conversion makes use of the ROLES setting.

E.g.

{
    'myview': [
        (True, is_admin),
        (False, is_user),
    ]
}
"""

import importlib

from django.conf import settings
from django.utils.module_loading import import_string
import django.core.exceptions as django_exceptions

from rest_framework_roles.exceptions import Misconfigured
from rest_framework_roles import decorators


def validate_config(config):
    if 'roles' not in config:
        raise django_exceptions.ImproperlyConfigured("Missing 'roles'")

    # TODO: Uncomment once we support view_permissions to be defined in settings
    # if 'view_permissions' not in config:
    #     raise django_exceptions.ImproperlyConfigured("Missing 'view_permissions'")


def load_view_permissions(config=None):
    """
    Load view permissioins from config
    """
    if not config:
        from django.conf import settings
        config = settings.REST_FRAMEWORK_ROLES
    validate_config(config)
    view_permissions = config['view_permissions']
    if isinstance(view_permissions, str):
        view_permissions = import_string(view_permissions)
    return view_permissions


def load_roles(config=None):
    """
    Load roles from config
    """
    if not config:
        from django.conf import settings
        config = settings.REST_FRAMEWORK_ROLES
    validate_config(config)
    roles = config['roles']
    if isinstance(roles, str):
        roles = import_string(roles)
    return roles


def parse_roles(roles_dict):
    """
    Parses given roles to a common structure that can be used for building the lookup

    Args:
        roles_dict: A dict where key is identifier of role, and value is a role_checker

    Output example:
    {
        'admin': {
            'role_name': 'admin',
            'role_checker': is_admin,
            'role_checker_cost': 50,
        }
    }
    """
    d = {}
    for role_name, role_checker in roles_dict.items():
        d[role_name] = {}
        d[role_name]['role_name'] = role_name
        d[role_name]['role_checker'] = role_checker
        try:
            cost = role_checker.cost
        except AttributeError:
            cost = decorators.DEFAULT_COST
            role_checker.cost = cost
        d[role_name]['role_checker_cost'] = cost
    return d


def parse_view_permissions(view_permissions, roles=None):
    """
    Transform all configuration into a lookup table to be used for permission checking

    Args:
        roles(dict): Dict where key is the role name and value is a dict with
                     role attributes
        view_permissions(dict): E.g. {'view': 'myview', 'permissions':[]}

    Output example:
        {
            'authentication.views.UserViewSet': {
                'create': [
                    (True, is_admin),
                    (False, is_anon),
                ]
            }
        }
    """
    lookup = {}
    if not roles:
        roles = load_roles()
    roles = parse_roles(roles)
    assert type(view_permissions) is dict, f"Expected view_permissions to be dict. Got {view_permissions}"
    assert type(roles) is dict, f"Expected roles to be dict. Got {roles}"

    # Check roles in permissions are correct before continuing
    roles_in_view_permissions = set()
    for permissions in view_permissions.values():
        for role in permissions.keys():
            roles_in_view_permissions.add(role)
    for role in roles_in_view_permissions:
        if role not in roles:
            raise Misconfigured(f"Role '{role}' given but such role not defined")

    # Populate general and instance checkers
    for view_name, permissions in view_permissions.items():
        lookup[view_name] = []
        for role, granted in permissions.items():
            lookup[view_name].append((
                granted,
                roles[role]['role_checker'],
            ))

    # Sort by cost
    for view, rules in lookup.items():
        rules.sort(key=lambda item: item[1].cost)

    return lookup


def get_lookup():
    roles = load_roles()
    view_permissions = load_view_permissions()
    return create_lookup(roles, view_permissions)
