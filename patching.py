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
from rest_framework_roles.exceptions import Misconfigured

logger = logging.getLogger(__name__)

DJANGO_CLASS_VIEWS = {
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


def patch(urlconf=None):
    """
    Entrypoint for all patching (after configurations have loaded)

    Essentially we look for the below

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """
    class_patterns = []
    function_patterns = []
    _all_patterns = get_urlpatterns(urlconf)
    for pattern in _all_patterns:
        if is_method_view(pattern.callback):
            class_patterns.append(pattern)
        else:
            function_patterns.append(pattern)

    # Patch simple function views directly
    for pattern in function_patterns:
        pattern.callback = before_view(pattern.callback)

    # Patch class based methods
    for pattern in class_patterns:
        cls = get_view_class(pattern.callback)
        views = []  # ..for patching

        # Find views by directive: view_permissions
        if hasattr(cls, 'view_permissions'):
            for d in cls.view_permissions.values():
                for view_name in d.keys():
                    if not hasattr(cls, view_name):
                        raise Misconfigured(f"Class '{cls.__name__}' has no method {view_name}")
                    views.append(view_name)

        # Find views by directive: decorators
        for resource_name in dir(cls):
            resource = getattr(cls, resource_name)
            if hasattr(resource, 'view_permissions'):
                views.append(resource_name)

        # Special case: Find REST views. These are annoying since they behave like nothing else.
        # TODO: Figure out the flow of this..
        #    1. Check if it is a REST function
        #    2. Patch all common methods available (get, post, etc.). This is OK
        #       since if it's a function then there will not be any custom method.
        #    3. Issue: We can't get the view name for use with PERMISSIONS_REGISTRY
        #       Solution: Patch the permission checking directly here
        #
        #  Redesign note
        #  -------------
        #
        #  Don't use PERMISSIONS_REGISTRY. Instead for every view with a directive
        #  do the below:
        #    1. Attach view_permissions directly to the view function
        #    2. Monkey patch view with before_view
        #    3. before_view will always make use of view.view_permissions when
        #       determining permissions.
        if hasattr(pattern.callback, '__wrapped__') and hasattr(pattern.callback, 'view_permissions'):
            import IPython; IPython.embed(using=False)

        # Perform patching
        for view_name in views:
            original_view = getattr(cls, view_name)
            setattr(cls, view_name, before_view(original_view))


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
