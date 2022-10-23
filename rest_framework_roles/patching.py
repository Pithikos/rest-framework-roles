"""
Patching occurs at runtime. However due to the nature of the flow of class-based views, this
can be more involved.

Below you can see the overall design on the patching process.

(Django patched)           (REST)                 (REST patched)
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


def wrapped_dispatch(dispatch):
    def pre_dispatch(self, request, *args, **kwargs):
        """
        Note that request.user not populated at this point
        """

        # Patch handler (as per Django and REST shared logic)
        verb = request.method.lower()
        if hasattr(self, verb):
            handler = getattr(self, verb)
            handler_permissions = None

            # Get handler permissions
            # NOTE: handler can e.g. be self.post but bound to 'create'
            if hasattr(handler, '_view_permissions'):
                handler_permissions = handler._view_permissions
            elif hasattr(self, '_view_permissions'):
                # REST CLASS
                if handler.__name__ in self._view_permissions:
                    handler_permissions = self._view_permissions[handler.__name__]
                elif verb in self._view_permissions:
                    handler_permissions = self._view_permissions[verb]

            # Patch view regardless if view_permissions found
            if handler_permissions:
                before = wrapped_view(
                    handler=handler,
                    handler_permissions=handler_permissions,
                    view_instance=self,
                )
                setattr(self, verb, before)

        # ---------------------------------------------------------------

        # In order to allow redirections we need to patch all methods of instance as per _view_permissions
        for handler_name, handler_permissions in self._view_permissions.items():
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                before = wrapped_view(handler, handler_permissions, view_instance=self)
                setattr(self, handler_name, before)
            else:
                raise Misconfigured(f"Specified view '{handler_name}' in view_permissions for class '{self.__name__}' but class has no such method")

        return dispatch(self, request, *args, **kwargs)

    return pre_dispatch


def wrapped_view(handler, handler_permissions, view_instance):
    def wrapped(request, *args, **kwargs):
        """
        Permissions MUST be checked at this point (and not earlier), since request.user
        is populated properly at this point
        """

        # Check permissions
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
    Entrypoint for all patching (after configurations have loaded)

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF


    patch ---- REST method ----.
         |                      --- patch dispatch ----> patch view
          '--- Django method --'
    """

    patterns = get_urlpatterns(urlconf)

    if not patterns:
        return


    for pattern in patterns:

        logger.debug(f'Traversing pattern: {pattern}')

        # Add pre_dispatch hooks for REST methods since patching needs to be done at runtime.
        cls = get_view_class(pattern.callback)
        try:
            cls.dispatch = wrapped_dispatch(cls.dispatch)
        except AttributeError as e:
            raise Exception(f"Can't patch view for {pattern}. Are you sure it's a class-based view?")
        
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
