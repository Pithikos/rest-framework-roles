DEFAULT_CHEAP = 0
DEFAULT_EXPENSIVE = 50


# ------------------------------------------------------------------------------


def allowed(*roles):
    pass


def disallowed(*roles):
    pass


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
