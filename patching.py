import sys

from django.urls import resolve, get_resolver
from django.conf import settings
from django.utils.functional import empty


def is_django_configured():
    return settings._wrapped is not empty


def is_rest_framework_loaded():
    return 'rest_framework' in sys.modules.keys()


def patch():
    # Ensure patching happens during the configuration of Django or after
    if is_django_configured():
        from .views import PatchedAPIView
        sys.modules['rest_framework'].views.APIView = PatchedAPIView


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
