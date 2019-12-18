import parsing
import exceptions

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

        fn.view_permissions = []
        for role, role_checker in role_checkers.items():
            if role in roles:
                fn.view_permissions.append((True, role_checker))
            else:
                fn.view_permissions.append((False, role_checker))

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

        fn.view_permissions = []
        for role, role_checker in role_checkers.items():
            if role in roles:
                fn.view_permissions.append((False, role_checker))
            else:
                fn.view_permissions.append((True, role_checker))

        return fn
    return wrapped


# ------------------------------------------------------------------------------


def cheap(*args, **kwargs):
    """
    Denote if role checker is cheap
    """
    cost = kwargs.get('cost', DEFAULT_CHEAP)
    assert cost < DEFAULT_EXPENSIVE, f"Must be below {DEFAULT_EXPENSIVE}, but given {cost}"

    def decorator(fn):
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped.cost = cost
        return wrapped
    decorator.cost = cost

    return decorator


def expensive(*args, **kwargs):
    """
    Denote if role checker is expensive
    """
    cost = kwargs.get('cost', DEFAULT_EXPENSIVE)
    assert cost >= DEFAULT_EXPENSIVE, f"Must be above {DEFAULT_EXPENSIVE}, but given {cost}"

    def decorator(fn):
        def wrapped(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped.cost = cost
        return wrapped
    decorator.cost = cost

    return decorator
