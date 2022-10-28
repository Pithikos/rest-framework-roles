DEFAULT_COST = 0
DEFAULT_EXPENSIVE = 50


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
