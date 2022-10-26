"""
Permissions are checked mainly by checking if a _view_permissions exist for given entity (function or class instance)
"""

import logging

from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from rest_framework_roles.exceptions import Misconfigured
from rest_framework_roles.granting import GrantChecker, bool_granted, TYPE_FUNCTION
from rest_framework_roles import exceptions
from rest_framework_roles import patching


MAX_VIEW_REDIRECTION_DEPTH = 3  # Disallow too much depth since it can potentially become expensive


logger = logging.getLogger(__name__)


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False


def bool_role(request, view, role):
    """ Checks if role evaluates to true """
    if hasattr(role, '__call__'):
        return role(request, view)
    elif type(role) != bool:
        raise exceptions.Misconfigured(f"Expected role to be boolean or callable, got '{role}'")
    return role


def check_permissions(request, view, view_instance, view_permissions=None):
    """
    Check if request is granted access or not

    Permission should be granted IF AND ONLY IF there's a matching role that
    explicitly grants permission. If no role was matched, access should be denied
    by default.

    Args:
        view_permissions(list): List of permissions for the specific request handler

    Return:
        Granted permission - True or False. None if no role matched.
    """
    assert isinstance(view_permissions, tuple) or view_permissions == None

    # Allow checking permissions again in case of redirected views
    if hasattr(request, "_permissions_checked"):
        if view in request._permissions_checked:
            raise Exception(f"Implementation bug. Permissions already checked by {view}")
        request._permissions_checked.add(view)
    else:
        request._permissions_checked = {view}  # Allows us to check if already been called

    if len(request._permissions_checked) > MAX_VIEW_REDIRECTION_DEPTH:
        raise Exception(f"Permissions checked too many times for same request: {request}")

    logger.debug(f'Check permissions for {request}..')

    # For decorated functions we check the permissions attached to the function
    if not view_permissions:
        try:
            view_permissions = view._view_permissions
        except AttributeError:
            raise Exception("No passed view_permissions and no attached _view_permissions found")

    # Determine permissions
    for permissions in view_permissions:
        granted, roles = permissions[0], permissions[1:]

        # Match any role
        for role in roles:
            if bool_role(request, view, role):

                role_name = role.__qualname__ if hasattr(role, '__qualname__') else role
                logger.debug(f"check_permissions:{view.__name__}:{role_name}:{granted}")

                # Check permission is granted:
                #   - We only return once we have evaluated positevely a granting rule.
                #     This is since if this rule doesn't grant permission, the next could.
                #   - We don't return False here, since *pre_view* will perform any other checks.
                #
                if type(granted) is bool:
                    pass
                elif type(granted) is TYPE_FUNCTION:
                    granted = bool_granted(request, view, granted, view_instance)
                elif type(granted) is GrantChecker:
                    granted = granted.evaluate(request, view, view_instance)
                else:
                    raise Misconfigured("From v0.4.0+ you need to use 'anyof', 'allof' or similar for multiple grant checks")

                if granted:
                    return granted