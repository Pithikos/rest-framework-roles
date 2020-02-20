import logging
from django.core.exceptions import PermissionDenied

from rest_framework_roles.decorators import DEFAULT_EXPENSIVE, role_checker
from rest_framework_roles import exceptions


logger = logging.getLogger(__name__)


@role_checker(cost=DEFAULT_EXPENSIVE)
def is_self(request, view):
    return request.user == view.get_object()


def bool_role(request, view, role):
    if hasattr(role, '__call__'):
        return role(request, view)
    elif type(role) != bool:
        raise exceptions.Misconfigured(f"Expected role to be boolean or callable, got '{role}'")
    return role


def bool_granted(request, view, granted, view_instance):
    if hasattr(granted, '__call__'):
        if view_instance:
            return granted(request, view=view_instance)
        else:
            return granted(request, view=view)
    elif type(granted) != bool:
        raise exceptions.Misconfigured(f"Expected granted to be boolean or callable, got '{granted}'")
    return granted


def check_permissions(request, view, view_instance):
    """
    Hook called for all 'guarded' views

    Return:
        Granted permission - True or False. None if no role matched.
    """

    if not hasattr(view, 'view_permissions'):
        raise Exception(f"View '{view}' is missing 'view_permissions'")

    for permissions in view.view_permissions:
        granted, roles = permissions[0], permissions[1:]

        # Match any role
        for role in roles:
            if bool_role(request, view, role):
                logger.debug(f"check_permissions:{view.__name__}:{role.__qualname__}:{granted}")
                if bool_granted(request, view, granted, view_instance):
                    return True

    # .. pre_view will perform any other checks ..
