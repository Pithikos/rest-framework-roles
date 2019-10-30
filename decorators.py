DEFAULT_CHEAP = 0
DEFAULT_EXPENSIVE = 50

# Permissions
def allowed(*roles):
    pass


def disallowed(*roles):
    pass


def permissions():
    pass


# Cost decorators
def cheap(fn, cost=DEFAULT_CHEAP):
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    assert DEFAULT_CHEAP <= cost < DEFAULT_EXPENSIVE
    wrapped.cost = cost
    return wrapped


def expensive(fn, cost=DEFAULT_EXPENSIVE):
    """
    Denote if role checker is expensive
    """
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    assert DEFAULT_EXPENSIVE <= cost
    wrapped.cost = cost
    return wrapped
