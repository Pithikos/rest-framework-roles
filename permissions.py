import logging
from django.core.exceptions import PermissionDenied

from .decorators import expensive
from . import exceptions


logger = logging.getLogger(__name__)


@expensive
def is_self(view, request):
    return request.user == view.get_object()


def bool_role(role, view, request):
    if hasattr(role, '__call__'):
        return role(view, request)
    elif type(role) != bool:
        raise exceptions.Misconfigured(f"Expected role to be boolean or callable, got '{role}'")
    return role


def bool_granted(granted, view, request):
    if hasattr(granted, '__call__'):
        return granted(view, request)
    elif type(granted) != bool:
        raise exceptions.Misconfigured(f"Expected granted to be boolean or callable, got '{granted}'")
    return granted


def check_permissions(self, request, view):
    """
    Hook called for all 'guarded' views

    Return:
        Granted permission - True or False. None if no role matched.
    """

    if not hasattr(view, 'view_permissions'):
        raise Exception(f"View '{view}' is missing 'view_permissions'")

    # import IPython; IPython.embed(using=False)
    for permissions in view.view_permissions:
        granted, roles = permissions[0], permissions[1:]

        # Match any role
        for role in roles:
            if bool_role(role, view, request):
                return bool_granted(granted, view, request)
