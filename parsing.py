import importlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .patching import is_django_configured


# Load settings for this module
if is_django_configured():
    if not hasattr(settings, 'REST_FRAMEWORK_ROLES'):
        raise ImproperlyConfigured("Missing 'REST_FRAMEWORK_ROLES' in settings")
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
    """ Read VIEW_PERMISSIONS from settings """
    assert 'view_permissions' in config, "Not set 'view_permissions'"
    pkgpath = '.'.join(config['view_permissions'].split('.')[:-1])
    dictkey = config['view_permissions'].split('.')[-1]
    pkg = importlib.import_module(pkgpath)
    view_permissions = getattr(pkg, dictkey)
    return view_permissions


def create_lookup(roles, view_permissions):
    """
    Transform all configuration into a lookup table to be used for permission checking

    Example:
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
    for view_rule in view_permissions:
        # view_class = importlib.import_module(view_rule['view'])
        view_path = view_rule['view']
        permissions = view_rule['permissions']
        lookup[view_path] = {}

        # Populate general and instance checkers
        for role, actions in permissions.items():
            for action, value in actions.items():

                if action not in lookup[view_path]:
                    lookup[view_path][action] = []

                lookup[view_path][action].append((
                    value,        # check if to be granted permission
                    roles[role],  # role checker
                ))
    return lookup


def get_lookup():
    roles = load_roles()
    view_permissions = load_view_permissions()
    return create_lookup(roles, view_permissions)
