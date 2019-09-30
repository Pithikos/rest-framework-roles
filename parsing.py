import importlib

from django.conf import settings

config = settings.REST_FRAMEWORK_ROLES


def load_roles():
    """ Load ROLES from settings """
    assert 'roles' in config, "Not set 'view_permissions'"
    pkgpath = '.'.join(config['roles'].split('.')[:-1])
    dictkey = config['roles'].split('.')[-1]
    pkg = importlib.import_module(pkgpath)
    roles = getattr(pkg, dictkey)
    return roles


def load_view_permissions():
    """ Read VIEW_PERMISSIONS from settings """
    assert 'view_permissions' in config, "Not set 'view_permissions'"
    pkgpath = '.'.join(config['view_permissions'].split('.')[:-1])
    dictkey = config['view_permissions'].split('.')[-1]
    pkg = importlib.import_module(pkgpath)
    view_permissions = getattr(pkg, dictkey)
    return view_permissions


def create_lookup():
    """
    Transform all configuration into a lookup table to be used for permission checking

    Output example:
        {
            'myapp.views.UserViewset': {
                'general_checkers': {
                    'create': [
                        is_anon
                    ],
                    'partial':
                },
                'instance_checkers': {
                    '*': [
                        is_owner
                    ]
                },
            }
        }
    """
    lookup = {}
    roles = load_roles()
    view_permissions = load_view_permissions()
    for view_rule in view_permissions:
        # view_class = importlib.import_module(view_rule['view'])
        view_path = view_rule['view']
        permissions = view_rule['permissions']
        lookup[view_path] = {}

        # Populate general and instance checkers
        for role, actions in permissions.items():
            checker = roles[role]['role_checker']
            for action, value in actions.items():
                if roles[role].get('check_instance'):
                    checker_type = 'instance_checkers'
                else:
                    checker_type = 'general_checkers'

                if checker_type not in lookup[view_path]:
                    lookup[view_path][checker_type] = {}

                try:
                    lookup[view_path][checker_type][action].append(checker)
                except KeyError:
                    lookup[view_path][checker_type][action] = [checker]

    return lookup
