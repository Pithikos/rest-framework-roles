from rest_framework_roles import exceptions


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

    SCHEMES = {
        'all': all,
        'any': any,
    }

    def __init__(self, scheme, checkers):
        assert scheme in self.SCHEMES.keys(), f"Invalid scheme; '{scheme}'. Must be one of {self.SCHEMES.keys()}"
        for checker in checkers:
            if type(checker) not in (TYPE_FUNCTION, bool):
                raise Exception("Grant checker must be either a boolean or a function evaluationg to boolean")
        self.scheme = scheme
        self.checkers = checkers

    def evaluate(self, request, view, view_instance):
        grants = [bool_granted(request, view, checker, view_instance) for checker in self.checkers]
        try:
            return self.SCHEMES[self.scheme](grants)
        except KeyError:
            raise Exception(f"Invalid scheme '{self.scheme}'")

    def __hash__(self):
        """
        NOTE: Hashing does not take into account request. We simply want to check
              that two GrantCheckers will check the same things
        """
        return hash(self.scheme) ^ hash(self.checkers)