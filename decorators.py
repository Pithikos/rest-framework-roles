# Permissions


def allowed(*roles):
    pass


def disallowed(*roles):
    pass


def permissions():
    pass


# Other
def expensive(fn, cost=1):
    """
    Mark role checking function as expensive

    Args:
        cost(int): Denotes the expensiveness of the check (0 is cheap, anything above is expensive).
                   Functions will be checked from cheapest to most expensive.
    """
    def wrapped(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapped
