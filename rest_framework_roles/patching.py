"""
Patching will use a mix of RolePermission and guarding views per-se (in cases where
RolePermission is not called by DRF, e.g. cyclic views or overriding Django's 
internals).
"""
import sys
import importlib
import logging

from django.urls import resolve, get_resolver
from django.urls.resolvers import URLPattern
from django.conf import settings
from django.utils.functional import empty
from django.core.exceptions import PermissionDenied

from rest_framework_roles import permissions
from rest_framework_roles.parsing import parse_view_permissions
from rest_framework_roles.exceptions import Misconfigured

logger = logging.getLogger(__name__)

HTTP_VERBS = {
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'head',
    'options',
    'trace',
}


def is_django_configured():
    return settings._wrapped is not empty


def is_rest_framework_loaded():
    return 'rest_framework' in sys.modules.keys()


# ------------------------------ Wrappers --------------------------------------


def is_rest_function(self):
    return self.__class__.__qualname__ == 'WrappedAPIView'


def retrieve_handler(self, request):
    """
    Get handler as per DRF

    self is the view class instance
    """

    # REF: https://github.com/encode/django-rest-framework/blob/master/rest_framework/views.py
    if request.method.lower() in self.http_method_names:
        handler = getattr(self, request.method.lower(),
                            self.http_method_not_allowed)
    else:
        handler = self.http_method_not_allowed

    return handler


def wrapped_dispatch(dispatch):
    def wrapped(self, request, *args, **kwargs):
        """
        Note that request.user not populated at this point so permission checking
        is not possible yet.
        """

        # Patch views for DRF class instances
        for handler_name, handler_permissions in self._view_permissions.items():
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                before = wrapped_view(handler, handler_permissions, view_instance=self)
                setattr(self, handler_name, before)
            else:
                raise Misconfigured(f"Could not find view '{handler_name}' specified in '{self.__class__.__name__}.view_permissions'")

        return dispatch(self, request, *args, **kwargs)

    return wrapped


def wrapped_view(handler, handler_permissions, view_instance):
    def wrapped(request, *args, **kwargs):
        """
        Permissions MUST be checked at this point (and not earlier), since request.user
        is populated properly at this point
        """

        # Check permissions when RolePermission could not
        if not hasattr(request, "_permissions_checked"):
            granted = permissions.check_permissions(request, handler, view_instance, handler_permissions)
            if not granted:
                raise PermissionDenied('Permission denied for user.')

        return handler(request, *args, **kwargs)
    return wrapped


# ------------------------------------------------------------------------------


def is_callback_method(callback):
    """
    Check if callback of pattern is a method
    """
    if hasattr(callback, 'view_class'):
        return True
    try:
        # Heurestic; all class methods end up calling the dispatch method
        return callback.__wrapped__.__wrapped__.__name__ == 'dispatch'
    except AttributeError:
        pass
    return False


def get_view_class(callback):
    """
    Try to get the class from given callback
    """
    if hasattr(callback, 'view_class'):
        return callback.view_class
    if hasattr(callback, 'cls'):
        return callback.cls
    # TODO: Below code seems to not do anything..
    mod = importlib.import_module(callback.__module__)
    cls = getattr(mod, callback.__name__)
    return cls


def patch(urlconf=None):
    """
    The patching will ensure RolePermission is used in permission_classes (unless already set)

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """

    patterns = get_urlpatterns(urlconf)

    if not patterns:
        return

    # Collect classes since multiple patterns might use the same view class
    collected_classes = set()
    for pattern in patterns:
        cls = get_view_class(pattern.callback)
        logger.debug(f'Collecting classes: {pattern} -> {cls}')
        collected_classes.add(cls)

    # Patch classes
    for cls in collected_classes:

        # Wrap dispatcher for cases where patching needs to be done at runtime.
        try:
            cls.dispatch = wrapped_dispatch(cls.dispatch)
        except AttributeError as e:
            raise Exception(f"Can't patch view for {pattern}. Are you sure it's a class-based view?")

        # Enforce RolePermission for every class
        if hasattr(cls, "permission_classes"):
            if permissions.RolePermission not in cls.permission_classes:
                if isinstance(cls.permission_classes, tuple):
                    cls.permission_classes = (permissions.RolePermission,) + cls.permission_classes
                else:
                    cls.permission_classes.insert(0, permissions.RolePermission)
        else:
            cls.permission_classes = [permissions.RolePermission]
        
        # Generate permissions for direct lookup
        if hasattr(cls, 'view_permissions'):
            cls._view_permissions = parse_view_permissions(cls.view_permissions)
        else:
            cls._view_permissions = {}


def get_urlpatterns(urlconf=None):
    if not urlconf:
        urlconf = importlib.import_module(settings.ROOT_URLCONF)
    assert type(urlconf) != str, f"URLConf should not be string. Got '{urlconf}'"
    url_patterns = list(iter_urlpatterns(urlconf.urlpatterns))
    return url_patterns


def iter_urlpatterns(urlpatterns):
    for entity in urlpatterns:
        if hasattr(entity, 'url_patterns'):
            yield from iter_urlpatterns(entity.url_patterns)
        elif hasattr(entity, 'urlpatterns'):
            yield from iter_urlpatterns(entity.urlpatterns)
        else:
            assert type(entity) == URLPattern, f"Expected pattern, got '{entity}'"
            yield entity


def extract_views_from_urlpatterns(urlpatterns):
    """
    Similar to iter_urlpatterns but uses django-extensions' show_urls methodology
    """
    from django_extensions.management.commands.show_urls import Command
    return Command().extract_views_from_urlpatterns(urlpatterns)
