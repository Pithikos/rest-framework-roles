import sys
import importlib

from django.urls import resolve, get_resolver
from django.urls.resolvers import URLPattern
from django.conf import settings
from django.utils.functional import empty


def is_django_configured():
    return settings._wrapped is not empty


def is_rest_framework_loaded():
    return 'rest_framework' in sys.modules.keys()


def patch(urlconf=None):
    """
    Entrypoint for all patching (after configurations have loaded)

    Args:
        urlconf(str): Path to urlconf, by default using ROOT_URLCONF
    """
    def before_view(target_view):
        def wrapped(request, *args, **kwargs):
            print('BEFORE VIEW..')
            import IPython; IPython.embed(using=False)
            return target_view(request, *args, **kwargs)
        return wrapped

    # Monkey-patch each view
    if not urlconf:
        urlconf = importlib.import_module(settings.ROOT_URLCONF)
    for pattern in iter_urlpatterns(urlconf.urlpatterns):
        pattern.callback = before_view(pattern.callback)


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
