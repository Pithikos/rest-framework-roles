DEFAULT_COST = 0
DEFAULT_EXPENSIVE = 50


def role_checker(fn=None, *, cost=DEFAULT_COST):
    """
    Allows marking a role checker with specific attributes, such as cost.

    Example:
        @role_checker(cost=50)
        def is_owner(view, request):
            ...
    """
    def decorator_role(fn):
        def wrapped_role(*args, **kwargs):
            return fn(*args, **kwargs)
        wrapped_role.cost = cost
        return wrapped_role
    decorator_role.cost = cost

    if fn is not None:
        return decorator_role(fn)
    return decorator_role