"""
Patching occurs at runtime. However due to the nature of the flow of class-based views, this
can be more involved.

Below you can see the overall design on the patching process.

(Django patched)            (REST)                 (REST patched)
      |                       |                          |
pre_dispatch --.              |                    pre_dispatch --.
               |              |                                   |
          patch handler       |                              patch handler
               |              |                                   |
   (optionally patch all      |                           (optionally patch all
    instance methods)         |                            instance methods)
               |              |                                   |
            dispatch       dispatch                            dispatch
               |              |                                   |
      .--------'              |                          .--------'
      |                       |                          |
      |                       |                          |
      |              REST check_permissions     REST check_permissions (mocked to do nothing)
      |                       |                          |
  pre_view ---.               |                      pre_view ----.
               |              |                                   |
        check_permissions     |                            check_permissions
               |              |                                   |
               |              |                           REST check_permissions (original)
               |              |                                   |
      .--------'              |                          .--------'
      |                       |                          |
     view                    view                       view


pre_dispatch
    - nullify self.check_permissions (and push to pre_view)
    - patch handler with pre_view
    - patch defined views in view_permissions with pre_view

pre_view
    - check_permissions
    - original_check_permissions

* Hooks pre_dispatch and pre_view are added in normal flow of Django and Django REST.
* pre_dispatch patches at runtime the handler and optionally all class instance methods. This allows redirections
* pre_view ensures that permissions are checked just before calling the actual view.
* In case of REST Framework the original REST check_permissions need to be pushed down after our
  own check_permissions.
* The main advantage of this way of patching is that the permissions remain view-bound.
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


def before_dispatch(dispatch):
    def pre_dispatch(self, request, *args, **kwargs):
        """
        Main purpose is to patch instance methods
        """

        # Attach _view_permissions to body of class
        if hasattr(self, 'view_permissions'):
            self._view_permissions = parse_view_permissions(self.view_permissions)

        # Dummify check_permissions for REST. This is needed if we patch the handler
        # or another viewset method.
        if hasattr(self, 'check_permissions'):
            original_check_permissions = self.check_permissions
            self.check_permissions = dummy_check_permissions
        else:
            original_check_permissions = None

        # Patch handler (as per Django and REST shared logic)
        verb = request.method.lower()
        if hasattr(self, verb):
            handler = getattr(self, verb)

            # Get permissions for handle
            # NOTE: handler can e.g. be self.post but bound to 'create'
            handler_permissions = None
            if hasattr(handler, '_view_permissions'):
                handler_permissions = handler._view_permissions

            # REST FUNCTION: Rest function. We use the class-based _view_permissions populated for the specific function
            elif is_rest_function(self):
                function_name = self.__class__.__name__
                handler_permissions = self._view_permissions[function_name]

            # REST CLASS
            elif hasattr(self, '_view_permissions'):
                if handler.__name__ in self._view_permissions:
                    handler_permissions = self._view_permissions[handler.__name__]
                elif verb in self._view_permissions:
                    handler_permissions = self._view_permissions[verb]

            else:
                logger.debug(f'No _view_permissions found for handler {handler} ({verb})')

            # Patch view
            if handler_permissions:
                before = before_view(
                    view=handler,
                    view_permissions=handler_permissions,
                    is_method=True,
                    view_instance=self,
                    original_check_permissions=original_check_permissions
                )
                setattr(self, verb, before)

        # ---------------------------------------------------------------

        # In order to allow redirections we need to patch all methods of instance as per _view_permissions
        if hasattr(self, '_view_permissions') and not is_rest_function(self):
            for view_name, permissions in self._view_permissions.items():
                if hasattr(self, view_name):
                    view = getattr(self, view_name)
                    before = before_view(view, permissions, is_method=True, view_instance=self, original_check_permissions=original_check_permissions)
                    setattr(self, view_name, before)
                else:
                    raise Misconfigured(f"Specified view '{view_name}' in view_permissions for class '{self.__name__}' but class has no such method")

        return dispatch(self, request, *args, **kwargs)

    return pre_dispatch


def before_view(view, view_permissions, is_method, view_instance, original_check_permissions):
    """
    Main wrapper for views

    Args:
        is_method(bool): Tells if the view is class-based
        view_instance: Only applicable for classes. Required for checking permissions in view redirections.

    Ensures permissions are checked before calling the view
    """

    def pre_view(view, request, self):
        logger.debug('Checking permissions..')

        # Try to find the right permission checks for the view
        granted = permissions.check_permissions(request, view, self, view_permissions)

        # Role matched and permission granted
        if granted:
            return

        # No matching role
        if granted == None and original_check_permissions:
            original_check_permissions(request)

        # Fallback for all other cases
        raise PermissionDenied('Permission denied for user.')

    def wrapped_function(request, *args, **kwargs):
        pre_view(view, request, None)
        return view(request, *args, **kwargs)

    def wrapped_method(request, *args, **kwargs):
        pre_view(view, request, view_instance)
        return view(request, *args, **kwargs)

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


def is_callback_rest_function(callback):
    # REST functions end up being methods after metaprogramming
    return is_callback_method(callback) and callback.__qualname__ == 'WrappedAPIView'


def dummy_check_permissions(self, *args):
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


def patch(urlconf=None):
    """
    Entrypoint for all patching (after configurations have loaded)

    We construct a view_table that is used for the actual patching.

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF



    patch ---- REST method ----.
         |                      --- patch dispatch ----> patch view
         |'--- Django method --/                         /
         |                    /                         /
         |'--- REST func  ---'                         /
         |                                            /
         '---- Django func --------------------------'
    """

    view_table = []  # list of (<pattern>, <viewname>, <class>, <view>, <permissions>, <original check_permissions>)

    patterns = get_urlpatterns(urlconf)

    if not patterns:
        return


    for pattern in patterns:

        logger.debug(f'Traversing pattern: {pattern}')

        # REST methods + functions. The functions end up being classes and behave excactly the same.
        if is_callback_rest_function(pattern.callback):

            # REST functions
            if is_callback_rest_function(pattern.callback) and hasattr(pattern.callback, '_view_permissions'):
                cls = get_view_class(pattern.callback)
                cls.dispatch = before_dispatch(cls.dispatch)

        # Add pre_dispatch hooks for REST methods since patching needs
        # to be done at runtime.
        elif is_callback_method(pattern.callback):
            cls = get_view_class(pattern.callback)
            cls.dispatch = before_dispatch(cls.dispatch)

        # Patch non
        elif hasattr(pattern.callback, '_view_permissions'):
            pattern.callback = before_view(
                view=pattern.callback,
                view_permissions=pattern.callback._view_permissions,
                is_method=False,
                view_instance=None,
                original_check_permissions=None,
            )

        else:
            logger.debug(f"Leaving view {pattern.callback} unpatched")


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
