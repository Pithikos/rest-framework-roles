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

PERMISSIONS_GRANTED_ATTR = "_rfr_permissions_granted"
VIEWS_CHECKED_ATTR = "_rfr_views_checked"


logger = logging.getLogger(__name__)


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False


def bool_role(request, view, role_checker):
    """ Checks if role evaluates to true """
    if hasattr(role_checker, '__call__'):
        return role_checker(request, view)
    elif type(role_checker) != bool:
        raise exceptions.Misconfigured(f"Expected role to be boolean or callable, got '{role_checker}'")
    return role_checker


def _check_role_permissions(request, view, view_instance, view_permissions):

    for permissions in view_permissions:
        granted, roles = permissions[0], permissions[1:]

        # Match any role
        for role in roles:
            if bool_role(request, view_instance, role):

                role_name = role.__qualname__ if hasattr(role, '__qualname__') else role
                logger.debug(f"check_role_permissions:{view.__name__}:{role_name}:{granted}")

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
                    permissions_granted = getattr(request, PERMISSIONS_GRANTED_ATTR, set())
                    permissions_granted.add(view_permissions)
                    setattr(request, PERMISSIONS_GRANTED_ATTR, permissions_granted)
                    return granted


def check_role_permissions(request, view, view_instance, view_permissions):
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

    # Catch too deep redirections
    views_checked = getattr(request, VIEWS_CHECKED_ATTR, set())
    if view in views_checked:
        raise Exception(f"Permissions already checked for {view}. Implementation bug?")
    views_checked.add(view)
    setattr(request, VIEWS_CHECKED_ATTR, views_checked)
    if len(views_checked) > MAX_VIEW_REDIRECTION_DEPTH:
        raise Exception(f"Permissions checked too many times for same request: {request}")

    # OPTIMIZATION: Avoid double-checking the same permissions twice
    permissions_granted = getattr(request, PERMISSIONS_GRANTED_ATTR, None)
    if permissions_granted and view_permissions in permissions_granted:
        return True

    logger.debug(f'Check permissions for {request}..')

    # Determine permissions
    return _check_role_permissions(request, view, view_instance, view_permissions)