TYPE_FUNCTION = type(lambda x: x)


def is_self(request, view):
    return request.user == view.get_object()


def allof(*grant_checkers):
    return GrantChecker('all', grant_checkers)


def anyof(*grant_checkers):
    return GrantChecker('any', grant_checkers)


def bool_granted(request, view, granted, view_instance):
    """ Checks if permission evaluates to true """
    if hasattr(granted, '__call__'):
        if view_instance:
            return granted(request, view=view_instance)
        else:
            return granted(request, view=view)
    elif type(granted) != bool:
        raise exceptions.Misconfigured(f"Expected granted to be boolean or callable, got '{granted}'")
    return granted


class GrantChecker():
    """
    Checks if grant should be given based on passed scheme and checkers
    """

    ALLOWED_SCHEMES = ('all', 'any')

    def __init__(self, scheme, checkers):
        assert scheme in self.ALLOWED_SCHEMES, f"Invalid scheme; '{scheme}'. Must be one of {self.ALLOWED_SCHEMES}"
        for checker in checkers:
            if type(checker) not in (TYPE_FUNCTION, bool):
                raise Exception("Grant checker must be either a boolean or a function evaluationg to boolean")
        self.scheme = scheme
        self.checkers = checkers

    def evaluate(self, request, view, view_instance):
        grants = [bool_granted(request, view, checker, view_instance) for checker in self.checkers]
        if self.scheme == 'all':
            return all(grants)
        elif self.scheme == 'any':
            return any(grants)
        else:
            raise Exception(f"Invalid scheme '{self.scheme}'")
