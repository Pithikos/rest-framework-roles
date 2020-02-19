"""
Patching is mainly about patching the desired views with the before_view function.
This ensures that permissions are checked before running the view. One of the big advantages
of this is that redirection will not bypass any permission checks.

Below you can see the overall design on the patching process.

(Django patched)            (REST)                 (REST patched)
  dispatch                 dispatch                   dispatch
      |                       |                          |
      |              REST check_permissions     REST check_permissions (mocked to do nothing)
      |                       |                          |
   pre_view                   |                     pre_view ------.
      |                       |                                     |
check_permissions             |                               check_permissions
      |                       |                                     |
      |                       |                        REST check_permissions (original)
      |                       |                                     |
    view                     view                      view  -------'
"""

import sys
import inspect
import importlib
import logging

from django.urls import resolve, get_resolver
from django.urls.resolvers import URLPattern
from django.conf import settings
from django.utils.functional import empty
from django.core.exceptions import PermissionDenied

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


VIEW_TABLE = None


def is_django_configured():
    return settings._wrapped is not empty


def is_rest_framework_loaded():
    return 'rest_framework' in sys.modules.keys()


# ------------------------------ Wrappers --------------------------------------


def before_view(view, is_method, original_check_permissions):
    """
    Main wrapper for views

    Args:
        is_method(bool): Tells if the view is class-based

    Ensures permissions are checked before calling the view
    """
    def pre_view(self, view, request):
        logger.debug('Checking permissions..')
        granted = check_permissions(request, view, self)

        # Role matched and permission granted
        if granted:
            return

        # No matching role
        if granted == None and original_check_permissions:
            original_check_permissions(self, request)

        # Fallback for all other cases
        raise PermissionDenied('Permission denied for user.')

    def wrapped_function(request, *args, **kwargs):
        pre_view(None, view, request)
        return view(request, *args, **kwargs)

    def wrapped_method(self, request, *args, **kwargs):
        pre_view(self, view, request)
        return view(self, request, *args, **kwargs)

    if is_method:
        return wrapped_method
    else:
        return wrapped_function


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


def dummy_check_permissions(self, request):
    """
    Dummy that replaces the REST class' check_permissions in order to not break
    the flow of REST Framework
    """
    return None


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


def is_callback_rest_function(callback):
    # REST functions end up being methods after metaprogramming
    return is_callback_method(callback) and callback.__qualname__ == 'WrappedAPIView'


def patch(urlconf=None):
    """
    Entrypoint for all patching (after configurations have loaded)

    We construct a view_table that is used for the actual patching.

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """

    view_table = []  # list of (<pattern>, <viewname>, <class>, <view>, <permissions>, <original check_permissions>)

    patterns = get_urlpatterns(urlconf)

    if not patterns:
        return

    # Populate view_table
    for pattern in patterns:
        if pattern.callback.__qualname__.startswith('before_view.'):
            raise exceptions.DoublePatching(f"View is already patched: {pattern.callback}")

        original_check_permissions = None  # Makes only sense for REST classes

        # Handle class-based views
        if is_callback_method(pattern.callback):
            cls = get_view_class(pattern.callback)

            # Special treatment for REST. We shuffle the original check_permissions
            # order so that it comes after our own and thus after the preview.
            if hasattr(cls, 'check_permissions'):
                original_check_permissions = cls.check_permissions

            # attached view_permissions to class
            if hasattr(cls, 'view_permissions'):
                view_permissions = parse_view_permissions(cls.view_permissions)
                for view_name, permissions in view_permissions.items():
                    if hasattr(cls, view_name):
                        view = getattr(cls, view_name)
                        view_table.append((pattern, view_name, cls, view, view_permissions[view_name], original_check_permissions))
                    else:
                        raise Misconfigured(f"Specified view '{view_name}' in view_permissions for class '{cls.__name__}' but class has no such method")

            # TODO: Also look in settings.
            pass

            # REST decorated methods
            for resource_name in dir(cls):
                resource = getattr(cls, resource_name)
                if hasattr(resource, 'view_permissions'): # == it was decorated
                    view_table.append((pattern, resource_name, cls, resource, resource.view_permissions, original_check_permissions))

            # REST functions
            if is_callback_rest_function(pattern.callback) and hasattr(pattern.callback, 'view_permissions'):
                cls = pattern.callback.cls

                if hasattr(cls, 'check_permissions'):
                    original_check_permissions = cls.check_permissions

                for view_name in HTTP_VERBS:
                    if not hasattr(cls, view_name):
                        continue
                    # NOTE: cls.get == cls.post since a func dealing with both
                    view = getattr(cls, view_name)
                    view_table.append((pattern, view_name, cls, view, pattern.callback.view_permissions, original_check_permissions))

        # Handle vanilla function views
        elif hasattr(pattern.callback, 'view_permissions'):
            view = pattern.callback
            view_table.append((pattern, view.__name__, None, view, view.view_permissions, original_check_permissions))

        else:
            # Vanilla undecorated function - do nothing. Ideally we would want to
            # add all views to the view_table. However this is impossible since there
            # is no way to figure out all the views of a class and thus patch them.
            pass

    # Populate global VIEW_TABLE. Note that VIEW_TABLE only holds views have been
    # explicitly
    global VIEW_TABLE
    VIEW_TABLE = {}
    for items in view_table:
        VIEW_TABLE[items[3]] = {
            'pattern': items[0],
            'view_class': items[2],
            'view': items[3],
            'permissions': items[4],
        }
    # Ensure full + relpath both include the changes
    sys.modules[__name__].VIEW_TABLE = VIEW_TABLE
    sys.modules['rest_framework_roles.%s' % __name__] = sys.modules[__name__]

    # Validate table
    for pattern, view_name, cls, view, view_permissions, original_check_permissions in view_table:
        assert type(view_name) is str
        assert type(view_permissions) is list, f"'view_permissions' must be list, got '{view_permissions}'"
        for item in view_permissions:
            assert type(item) is tuple, f"Expected each item in 'view_permissions' to be tutple. Got '{item}'"
        assert original_check_permissions is None or hasattr(original_check_permissions, '__call__')

    # Perform patching
    for pattern, view_name, cls, view, view_permissions, original_check_permissions in view_table:
        view.view_permissions = view_permissions

        # Ensure REST's check_permissions is always going to pass if called before before_view
        if original_check_permissions:
            cls.check_permissions = dummy_check_permissions

        if cls:
            before = before_view(view, is_method=True, original_check_permissions=original_check_permissions)
        else:
            before = before_view(view, is_method=False, original_check_permissions=original_check_permissions)

        before._view_permissions = view_permissions  # we attach permissions to before_view as well
                                                     # to make debugging easier
        if cls:
            setattr(cls, view_name, before)
        else:
            pattern.callback = before


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
