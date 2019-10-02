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
                'create': {
                    'role_checkers': [
                        is_anon
                    ],
                },
                '*': {
                    'role_object_checkers': [
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
            checker = roles[role]
            for action, value in actions.items():

                extra = None
                if ':' in action:
                    action, extra = action.split(':')

                if action not in lookup:
                    lookup[view_path][action] = {
                        'role_object_checkers': [],
                        'role_checkers': [],
                        'extra': extra,
                    }

                if hasattr(roles[role], 'has_object_role'):
                    checker_type = 'role_object_checkers'
                else:
                    checker_type = 'role_checkers'
                lookup[view_path][action][checker_type].append(checker)

    return lookup
