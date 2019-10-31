import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

# from .patching import is_django_configured
from .decorators import DEFAULT_COST


class InvalidConfiguration(Exception):
    pass


def validate_settings():
    if not hasattr(settings, 'REST_FRAMEWORK_ROLES'):
        raise ImproperlyConfigured("Missing 'REST_FRAMEWORK_ROLES' in settings")
    roles_config = settings.REST_FRAMEWORK_ROLES
    required_keys = ['view_permissions']
    for k in required_keys:
        if k not in roles_config:
            raise ImproperlyConfigured(f"'REST_FRAMEWORK_ROLES' is missing required settings '{k}'")


# Load settings for this module
if is_django_configured():
    validate_settings()
    config = settings.REST_FRAMEWORK_ROLES
else:
    raise Exception(f"Must setup Django settings before loading '{__name__}'")


def load_roles():
    """ Load ROLES from settings """
    assert 'roles' in config, "Not set 'view_permissions'"
    pkgpath = '.'.join(config['roles'].split('.')[:-1])
    dictkey = config['roles'].split('.')[-1]
    pkg = importlib.import_module(pkgpath)
    roles = getattr(pkg, dictkey)
    return roles


def load_view_permissions():
    """ Read VIEW_PERMISSIONS from Django settings """
    pkgpath = '.'.join(config['view_permissions'].split('.')[:-1])
    dictkey = config['view_permissions'].split('.')[-1]
    pkg = importlib.import_module(pkgpath)
    view_permissions = getattr(pkg, dictkey)
    return view_permissions


def parse_roles(roles_dict):
    """
    Parses given roles to a common structure that can be used for building the lookup
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
        d[role_name]['role_checker_cost'] = cost
    return d


def parse_permissions(view_permissions, merge_same_views=True):
    """
    Parses permissions to a uniform more verbose format

    Args:
        merge_same_views(bool): Merge rules for the same views
    """

    # Deconstruct concise syntax for class-based views
    for i, rule in enumerate(view_permissions):
        view = rule['view']
        permissions = rule['permissions']
        new_rules = []
        for role_name, unknown in permissions.items():
            if isinstance(unknown, dict):
                for method_name, granted in unknown.items():
                    new_rule = {
                        'view': f"{view}.{method_name}",
                        'permissions': {role_name: granted},
                    }
                    new_rules.append(new_rule)
        if new_rules:
            for new_rule in reversed(new_rules):
                view_permissions.insert(i+1, new_rule)
            del view_permissions[i]

    # Merge rules for same views
    if merge_same_views:
        new_view_permissions = []
        all_views = [rule['view'] for rule in view_permissions]
        added = set()

        for i, rule in enumerate(view_permissions):
            if rule['view'] in added:
                continue
            indice = [j for j, r in enumerate(view_permissions) if r['view'] == rule['view']]
            if len(indice) > 1:
                permissions_to_combine = [view_permissions[j]['permissions'] for j in indice]

                # Check for duplicates
                role_names = []
                for d in permissions_to_combine:
                    role_names.extend(d.keys())
                for role_name in role_names:
                    if role_names.count(role_name) > 1:
                        raise InvalidConfiguration(f'You have set permissions for {role_name} more than once')

                permissions_combined = {}
                for d in permissions_to_combine:
                    permissions_combined.update(d)

                new_view_permissions.append({
                    'view': rule['view'],
                    'permissions': permissions_combined,
                })
                added.add(rule['view'])
            else:
                new_view_permissions.append(rule)
        view_permissions = new_view_permissions

    return view_permissions


def create_lookup(roles, view_permissions):
    """
    Transform all configuration into a lookup table to be used for permission checking

    Args:
        roles(list): A list of str or role checking

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
    roles = parse_roles(roles)
    view_permissions = parse_permissions(view_permissions)

    for view_rule in view_permissions:
        view = view_rule['view']
        permissions = view_rule['permissions']
        lookup[view] = []

        # Populate general and instance checkers
        for role, granted in permissions.items():
            lookup[view].append((
                granted,
                roles[role]['role_checker'],
            ))

    # Sort by cost
    # for view, rules in lookup.items():
    #     for action
    #     import IPython; IPython.embed(using=False)
    return lookup


# def add_to_lookup(permissions):



def get_lookup():
    roles = load_roles()
    view_permissions = load_view_permissions()
    return create_lookup(roles, view_permissions)
