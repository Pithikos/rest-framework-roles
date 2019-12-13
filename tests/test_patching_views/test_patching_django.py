import importlib
from unittest.mock import patch

import pytest
import django
from django.urls import get_resolver
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.urls import path
from django.http import HttpResponse

# from .urls import *
import patching
from decorators import allowed
from ..utils import _func_name, is_patched


# -------------------------------- Setup app -----------------------------------


@allowed('admin')
def django_function_view_decorated(request):
    return HttpResponse(_func_name())


def django_function_view_undecorated(request):
    return HttpResponse(_func_name())


class DjangoView(django.views.generic.ListView):
    model = User

    view_permissions = {
        'admin': {
            'view_patched_by_view_permissions': True,
        }
    }

    # This is the vanilla view - unpatched
    def get(self, request):
        return HttpResponse(_func_name())

    def view_unpatched(self, request):
        return HttpResponse(_func_name())

    def view_patched_by_view_permissions(self, request):
        return HttpResponse(_func_name())

    @allowed('admin')
    def view_patched_by_decorator(self, request):
        return HttpResponse(_func_name())


urlpatterns = [
    path('django_function_view_decorated', django_function_view_decorated),
    path('django_function_view_undecorated', django_function_view_undecorated),
    path('django_class_view', DjangoView.as_view()),
]


# ------------------------------------------------------------------------------


urlconf = importlib.import_module(__name__)
patching.patch(urlconf)
resolver = get_resolver(urlconf)


def test_function_views_patched_regardless_of_directives():
    # Normally we patch only views that are targeted by directives (e.g. decorators).
    # Vanilla Django function views are the exception, and are patched directly
    # regardless, in order to simplify things.
    match = resolver.resolve('/django_function_view_decorated')
    assert is_patched(match.func)
    match = resolver.resolve('/django_function_view_undecorated')
    assert is_patched(match.func)


def test_method_views_patched_with_directives_only():
    match = resolver.resolve('/django_class_view')
    cls = match.func.view_class

    assert not is_patched(cls.view_unpatched)
    assert not is_patched(cls.get)  # since no directive
    assert is_patched(cls.view_patched_by_view_permissions)
    assert is_patched(cls.view_patched_by_decorator)
