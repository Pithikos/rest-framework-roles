"""
Patching is mainly about patching the desired views with the before_view function.
This ensures that permissions are checked before running the view.
"""

import sys
import inspect
import importlib
import logging

from django.urls import resolve, get_resolver
from django.urls.resolvers import URLPattern
from django.conf import settings
from django.utils.functional import empty

from rest_framework_roles.permissions import check_permissions
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

def before_view(view):
    """
    Main wrapper for views

    Ensures permissions are checked before calling the view
    """

    def pre_view(request, view):
        logger.debug('Checking permissions..')
        check_permissions(request, view)

    def wrapped_function(request, *args, **kwargs):
        pre_view(request, view)
        return view(request, *args, **kwargs)

    def wrapped_method(self, request, *args, **kwargs):
        pre_view(request, self)
        return view(self, request, *args, **kwargs)

    if is_method_view(view):
        return wrapped_method
    else:
        return wrapped_function


# ------------------------------------------------------------------------------


def is_method_view(callback):
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
    mod = importlib.import_module(callback.__module__)
    cls = getattr(mod, callback.__name__)
    return cls


def is_rest_function_view(callback):
    # REST functions end up being methods after metaprogramming
    return is_method_view(callback) and callback.__qualname__ == 'WrappedAPIView'


def create_permission_table(urlpatterns):
    """
    Creates a table where keys are views and values are permissions
    """
    pass


def patch(urlconf=None):
    """
    Entrypoint for all patching (after configurations have loaded)

    Essentially we look for the below

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """

    view_table = []  # list of (<pattern>, <viewname>, <class>, <view>, <permissions>)

    # Populate view_table
    for pattern in get_urlpatterns(urlconf):

        if pattern.callback.__qualname__.startswith('before_view.'):
            raise exceptions.DoublePatching(f"View is already patched: {pattern.callback}")

        # Handle class-based views
        if is_method_view(pattern.callback):
            cls = get_view_class(pattern.callback)

            # attached view_permissions to class
            if hasattr(cls, 'view_permissions'):
                view_permissions = parse_view_permissions(cls.view_permissions)
                for view_name, permissions in view_permissions.items():
                    if hasattr(cls, view_name):
                        view = getattr(cls, view_name)
                        view_table.append((pattern, view_name, cls, view, view_permissions))
                    else:
                        raise Misconfigured(f"Specified view '{view_name}' in view_permissions for class '{cls.__name__}' but class has no such method")

            # TODO: Also look in settings.
            pass

            # REST decorated methods
            for resource_name in dir(cls):
                resource = getattr(cls, resource_name)
                if hasattr(resource, 'view_permissions'): # == it was decorated
                    view_table.append((pattern, resource_name, cls, resource, resource.view_permissions))

            # REST functions
            if is_rest_function_view(pattern.callback) and hasattr(pattern.callback, 'view_permissions'):
                cls = pattern.callback.cls
                for view_name in HTTP_VERBS:
                    if not hasattr(cls, view_name):
                        continue
                    # NOTE: For some reason cls.get == cls.post
                    view = getattr(cls, view_name)
                    view_table.append((pattern, view_name, cls, view, pattern.callback.view_permissions))

        # Handle vanilla function views
        elif hasattr(pattern.callback, 'view_permissions'):
            view = pattern.callback
            view_table.append((pattern, view.__name__, None, view, view.view_permissions))

        else:
            # Vanilla undecorated function - do nothing
            pass

    # Perform patching
    for pattern, view_name, cls, view, view_permissions in view_table:
        view.view_permissions = permissions
        if cls:
            setattr(cls, view_name, before_view(view))
        else:
            pattern.callback = before_view(view)


def get_urlpatterns(urlconf=None):
    if not urlconf:
        urlconf = importlib.import_module(settings.ROOT_URLCONF)
    assert type(urlconf) != str, f"URLConf should not be string. Got '{urlconf}'"
    url_patterns = list(iter_urlpatterns(urlconf.urlpatterns))
    return url_patterns

    function_patterns = []
    _all_patterns = get_urlpatterns(urlconf)
    for pattern in _all_patterns:
        if is_method_view(pattern.callback):
            class_patterns.append(pattern)
        else:
            function_patterns.append(pattern)
    function_patterns = []
    _all_patterns = get_urlpatterns(urlconf)
    for pattern in _all_patterns:
        if is_method_view(pattern.callback):
            class_patterns.append(pattern)
        else:
            function_pa


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
