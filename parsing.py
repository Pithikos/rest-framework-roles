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
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .decorators import DEFAULT_COST
from .utils import dotted_path


class InvalidConfiguration(Exception):
    pass


def validate_config(config):
    required_keys = ['view_permissions']
    for k in required_keys:
        if k not in config:
            raise ImproperlyConfigured(f"Missing required setting '{k}'")


def load_config(dotted_path=None):
    KEY_NAME = 'REST_FRAMEWORK_ROLES'
    if not dotted_path:
        config = getattr(settings, KEY_NAME)
    else:
        mod = import_string(dotted_path)
        config = getattr(mod, KEY_NAME)

        config['roles'] = load_roles(config)
        config['view_permissions'] = load_view_permissions(config)

    validate_config(config)
    return config


def load_roles(config):
    """
    Load roles (we only check at settings file)
    """
    roles = config['roles']
    if isinstance(roles, str):
        roles = import_string(roles)
    return roles


def parse_roles(roles_dict):
    """
    Parses given roles to a common structure that can be used for building the lookup

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
            cost = DEFAULT_COST
            role_checker.cost = cost
        d[role_name]['role_checker_cost'] = cost
    return d


def parse_view_permissions(view_permissions, roles=None):
    """
    Transform all configuration into a lookup table to be used for permission checking

    Args:
        roles(list): A list of str or role checking
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
        roles = load_roles(config=settings.REST_FRAMEWORK_ROLES)
    roles = parse_roles(roles)
    assert type(view_permissions) is dict, f"Expected view_permissions to be dict. Got {view_permissions}"

    for view_name, permissions in view_permissions.items():
        # Populate general and instance checkers
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
