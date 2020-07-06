"""
Permissions are checked mainly by checking if a _view_permissions exist for given entity (function or class instance)
"""

import logging
from django.core.exceptions import PermissionDenied

from rest_framework_roles.granting import GrantChecker, bool_granted, TYPE_FUNCTION
from rest_framework_roles import exceptions


logger = logging.getLogger(__name__)


def bool_role(request, view, role):
    """ Checks if role evaluates to true """
    if hasattr(role, '__call__'):
        return role(request, view)
    elif type(role) != bool:
        raise exceptions.Misconfigured(f"Expected role to be boolean or callable, got '{role}'")
    return role


def check_permissions(request, view, view_instance, view_permissions=None):
    """
    Hook called for all 'guarded' views

    Return:
        Granted permission - True or False. None if no role matched.
    """

    logger.debug('Check permissions..')

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
                if type(granted) is bool and granted:
                    return True
                elif type(granted) is TYPE_FUNCTION:
                    if bool_granted(request, view, granted, view_instance):
                        return True
                elif type(granted) is GrantChecker:
                    if granted.evaluate(request, view, view_instance):
                        return True
