from rest_framework_roles import parsing
from rest_framework_roles import exceptions

DEFAULT_CHEAP = 0
DEFAULT_EXPENSIVE = 50
DEFAULT_COST = DEFAULT_CHEAP

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


def cheap(*args, **kwargs):
    """
    Denote if role checker is cheap
    """
    cost = kwargs.get('cost', DEFAULT_CHEAP)
    assert cost < DEFAULT_EXPENSIVE, f"Must be below {DEFAULT_EXPENSIVE}, but given {cost}"

    def decorator_cheap(fn):
        def wrapped_cheap(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped_cheap.cost = cost
        return wrapped_cheap
    decorator_cheap.cost = cost

    if args and callable(args[0]):
        return decorator_cheap(*args)
    else:
        return decorator_cheap


def expensive(*args, **kwargs):
    """
    Denote if role checker is expensive
    """
    cost = kwargs.get('cost', DEFAULT_EXPENSIVE)
    assert cost >= DEFAULT_EXPENSIVE, f"Must be above {DEFAULT_EXPENSIVE}, but given {cost}"

    def decorator_expensive(fn):
        def wrapped_expensive(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped_expensive.cost = cost
        return wrapped_expensive
    decorator_expensive.cost = cost

    if args and callable(args[0]):
        return decorator_expensive(*args)
    else:
        return decorator_expensive
