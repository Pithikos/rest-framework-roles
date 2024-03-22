import sys
import importlib
import logging
import fnmatch
from functools import wraps

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


DEFAULT_SKIP_MODULES = {
    "django.*"
}


DENY_ALL_PERMISSION = [(True, False)]  # Evaluates role always to True and granted to False


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
    """

    # REF: https://github.com/encode/django-rest-framework/blob/master/rest_framework/views.py
    if request.method.lower() in self.http_method_names:
        handler = getattr(self, request.method.lower(),
                            self.http_method_not_allowed)
    else:
        handler = self.http_method_not_allowed

    return handler


def _rfr_wrap_handler(handler, handler_permissions):

    @wraps(handler)  # Preserve original function's metadata
    def _rfr_wrapped_handler(self, request, *args, **kwargs):
        """
        A wrapped view is the view that was explicitly mentioned in view_permissions,
        hence it shall ALWAYS check for permissions.
        """

        granted = permissions.check_role_permissions(request, handler, self, handler_permissions)
        if not granted:
            raise PermissionDenied('Permission denied for user.')

        return handler(self, request, *args, **kwargs)
    
    return _rfr_wrapped_handler


def _rfr_wrap_check_permissions(original_check_permissions):
    def _rfr_wrapped_check_permissions(self, request):
        """
        Bypass normal check_permissions behaviour when we use check_role_permissions
        """
        handler = retrieve_handler(self, request)

        def is_explicitly_protected(self, request):
            """
            Determine if request handler is mentioned in view_permissions
            """

            if handler.__name__ in self._view_permissions:
                return True

            if handler.__qualname__.endswith("._rfr_wrapped_handler"): # TRUE
                # If we have wrapped the handler, it means that it was due
                # to being explicitly mentioned in view_permissions
                return True

            if getattr(self, "action", None):
                # e.g. ModelViewSet, ViewSet
                if self.action in self._view_permissions:
                    return True

            # If we can't determine the final handler at this point.
            # So for safety we return assuming there isn't one
            return False

        # Deny access when no corresponding handler found in view_permissions
        #
        # This is since in that case, _rfr_wrap_handler will never fire and hence
        # neither will check_permissions. So we fallback to denying access for
        # these cases.
        if handler.__name__ == "http_method_not_allowed":
            # Allow 405 to be returned
            return
        elif not is_explicitly_protected(self, request):
            logger.warning(f"{self.__class__.__name__}: Handler '{handler.__name__}' fired but no explicit permission found in 'view_permissions' for this handler. Denying access")
            raise PermissionDenied('Permission denied for user.')

    return _rfr_wrapped_check_permissions


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


def patch(urlconf=None, roleconfig=None):
    """
    Do the patching starting from the URLs

    Original DRF flow:
        1. dispatch()
            2. initial()
                3.check_permissions()
            4. handler()
            5. finalize_response()

    Patched flow:
        1. dispatch()
            2. _rfr_wrap_handler()
                3. check_role_permissions()
                4. handler()
                5. finalize_response()

    Our aim is to protect mentioned views in view_permissions. For view_permissions
    but with non-mentioned views the default behaviour is to deny permission.

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """
    from django.conf import settings
    SKIP_MODULES = settings.REST_FRAMEWORK_ROLES.get("SKIP_MODULES", DEFAULT_SKIP_MODULES)

    # Patch DRF's default permission_classes
    from rest_framework.settings import api_settings  # noqa
    api_settings.DEFAULT_PERMISSION_CLASSES = [permissions.DenyAll]

    patterns = get_urlpatterns(urlconf)

    if not patterns:
        return

    # Collect classes since multiple patterns might use the same view class
    collected_classes = set()
    for pattern in patterns:
        
        # Skip patching 3rd party entities (e.g. django.contrib.admin)
        skip = False
        for modpattern in SKIP_MODULES:
            if fnmatch.filter([pattern.callback.__module__], modpattern):
                logger.debug(f"Skip patching {pattern.callback}")
                skip = True
                break
        if skip:
            continue

        cls = get_view_class(pattern.callback)
        logger.debug(f'Collecting classes: {pattern} -> {cls}')
        collected_classes.add(cls)

    # Get classes that need patching
    patch_classes = []
    for cls in collected_classes:
        if hasattr(cls, "view_permissions"):
            patch_classes.append(cls)

    # Patch classes
    for cls in patch_classes:

        # Raise exception if by mistake class has both view_permissions and permission_classes since
        # they can't work together. Note this will not catch the rare occassion that permission_classes = [DenyAll]
        permission_classes = getattr(cls, "permission_classes", None)
        if permission_classes and permission_classes != api_settings.DEFAULT_PERMISSION_CLASSES:
            raise Misconfigured(f"{cls.__name__}: You can't use both 'permission_classes' and 'view_permissions' in the same class")
        
        # Parse permissions for direct lookup
        cls._view_permissions = parse_view_permissions(cls.view_permissions, roleconfig)
        
        # Wrap mentioned request handler in view_permissions.
        for handler_name, handler_permissions in cls._view_permissions.items():
            if hasattr(cls, handler_name):
                handler_permissions = cls._view_permissions[handler_name]
                old_handler = getattr(cls, handler_name)
                new_handler = _rfr_wrap_handler(old_handler, handler_permissions)
                setattr(cls, handler_name, new_handler)
            else:
                raise Misconfigured(f"Unknown method '{handler_name}' found in {cls.__name__}.view_permissions")

        # Wrap DRF's check_permissions
        if hasattr(cls, "check_permissions"):
            cls.check_permissions = _rfr_wrap_check_permissions(cls.check_permissions)

    return patch_classes


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
