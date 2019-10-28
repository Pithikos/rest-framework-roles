import sys
import inspect
import importlib

from django.urls import resolve, get_resolver
from django.urls.resolvers import URLPattern
from django.conf import settings
from django.utils.functional import empty


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


DJANGO_REST_CLASS_VIEWS = {
    'list',
    'create',
    'retrieve',
    'update',
    'partial_update',
    'destroy',
}


def is_django_configured():
    return settings._wrapped is not empty


def is_rest_framework_loaded():
    return 'rest_framework' in sys.modules.keys()


def before_view(request, view, *args, **kwargs):
    """
    Hook called just before every view
    """
    print(f'BEFORE VIEW.. : {request.user}')
    # dispatchview.__wrapped__.__wrapped__
    # original_func = view.__wra


def function_view_wrapper(view):
    def wrapped(request, *args, **kwargs):
        print('INSIDE function_view_wrapper.wrapped()..')
        # import IPython; IPython.embed(using=False)
        before_view(request, view, *args, **kwargs)
        return view(request, *args, **kwargs)
    return wrapped


def class_view_wrapper(view):
    def wrapped(self, request, *args, **kwargs):
        print('INSIDE class_view_wrapper.wrapped()..')
        # import IPython; IPython.embed(using=False)
        before_view(request, self, *args, **kwargs)  # Note we pass the class as view instead of function
        return view(self, request, *args, **kwargs)
    return wrapped


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

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """
    if not urlconf:
        urlconf = importlib.import_module(settings.ROOT_URLCONF)
    assert type(urlconf) != str, f"URLConf should not be string. Got '{urlconf}'"

    # Get all active patterns
    patterns = list(iter_urlpatterns(urlconf.urlpatterns))
    class_patterns = []
    function_patterns = []
    for pattern in patterns:
        if is_method_view(pattern.callback):
            class_patterns.append(pattern)
        else:
            function_patterns.append(pattern)

    # Patch simple function views directly
    for pattern in function_patterns:
        pattern.callback = function_view_wrapper(pattern.callback)

    # Path class method
    for pattern in class_patterns:
        cls = pattern.callback.view_class  # populated after as_view()

        # Get the Django 'client' methods - essentially the view methods
        # For a simple rest_function_view this would be 'get' and 'options'
        methods = set(dir(cls)) & DJANGO_CLASS_VIEWS

        # Actual patching of method
        for method_name in methods:
            original_method = getattr(cls, method_name)
            setattr(cls, method_name, class_view_wrapper(original_method))


def get_active_views():
    views = []
    for view in get_resolver().reverse_dict.keys():
        if hasattr(view, '__call__'):
            views.append(view)
        elif type(view) is str:
            views.append(resolve(view))
        else:
            raise Exception('View must be callable or string')
    return views


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
