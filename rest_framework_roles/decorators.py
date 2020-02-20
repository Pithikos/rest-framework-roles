from rest_framework_roles import parsing
from rest_framework_roles import exceptions

DEFAULT_COST = 0
DEFAULT_EXPENSIVE = 50

# ------------------------------------------------------------------------------


def allowed(*roles):
    """
    Allow only given roles to access view. Any other roles will be denied access.
    """
    def wrapped(fn):
        role_checkers = parsing.load_roles()

        # Check first roles are valid
        for r in roles:
            if r not in role_checkers:
                raise exceptions.Misconfigured(f"Invalid role '{r}'")
        if hasattr(fn, 'view_permissions'):
            raise Exception(f"Unexpected existing 'view_permissions' for '{fn}'")

        fn.view_permissions = []
        for role in roles:
            fn.view_permissions.append((True, role_checkers[role]))

        return fn
    return wrapped


def disallowed(*roles):
    """
    Deny access for given roles. Any other roles will be allowed access.
    """
    def wrapped(fn):
        role_checkers = parsing.load_roles()

        # Check first roles are valid
        for r in roles:
            if r not in role_checkers:
                raise exceptions.Misconfigured(f"Invalid role '{r}'")
        if hasattr(fn, 'view_permissions'):
            raise Exception(f"Unexpected existing 'view_permissions' for '{fn}'")

        fn.view_permissions = []
        for role in roles:
            fn.view_permissions.append((False, role_checkers[role]))

        return fn
    return wrapped


# ------------------------------------------------------------------------------


def role_checker(*args, **kwargs):
    """
    Denote if role checker is cheap
    """
    cost = kwargs.get('cost', DEFAULT_COST)

    def decorator_role(fn):
        def wrapped_role(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped_role.cost = cost
        return wrapped_role
    decorator_role.cost = cost

    if args and callable(args[0]):
        return decorator_role(*args)
    else:
        return decorator_role
