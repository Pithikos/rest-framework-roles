import importlib

from django.conf import settings
from django.utils.module_loading import import_string
import django.core.exceptions as django_exceptions

from rest_framework_roles.exceptions import Misconfigured
from rest_framework_roles import decorators


VALID_SETTINGS = {"ROLES", "SKIP_MODULES"}
REQUIRED_SETTINGS = {"ROLES"}


def validate_config(config):
    for setting in config.keys():
        if setting not in VALID_SETTINGS:
            raise django_exceptions.ImproperlyConfigured(f"Unknown setting '{setting}'")
    for required_setting in REQUIRED_SETTINGS:
        if required_setting not in config:
            raise django_exceptions.ImproperlyConfigured(f"Missing required setting '{required_setting}'")


def load_settings(config=None):
    if not config:
        from django.conf import settings
        config = settings.REST_FRAMEWORK_ROLES
    validate_config(config)
    return config


def load_roles(config=None):
    """
    Load roles from config
    """
    settings = load_settings(config)
    roles = settings['ROLES']
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


def get_permission_list(parsed_roles, raw_permissions):
    _permissions = []
    for role, granted in raw_permissions.items():
        _permissions.append((
            granted,
            parsed_roles[role]['role_checker'],
        ))
    return _permissions


def parse_view_permissions(view_permissions, roles=None):
    """
    Transform view_permissions into a lookup table that can be used directly for checking permissions
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
            raise Misconfigured(f"Role '{role}' found in view_permissions but such role not defined in ROLES")

    # Populate general and instance checkers
    for view_names, permissions in view_permissions.items():
        _permissions = get_permission_list(roles, permissions)
        for view_name in view_names.split(","):
            lookup[view_name] = _permissions

    # Sort by cost
    for view, rules in lookup.items():
        rules.sort(key=lambda item: item[1].cost)

    # Finally turn into tuples for easy hashing
    for view, rules in lookup.items():
        lookup[view] = tuple(rules)

    return lookup