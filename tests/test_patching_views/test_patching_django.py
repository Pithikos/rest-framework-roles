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
from ..utils import _func_name


# -------------------------------- Setup app -----------------------------------


def django_function_view(request):
    return HttpResponse(_func_name())


class DjangoView(django.views.generic.ListView):
    model = User

    def get(self, request):
        return HttpResponse(_func_name())

    def not_a_view(self, *args, **kwargs):
        # Not a view since not the standard get, post, etc.
        return HttpResponse(_func_name())


urlpatterns = [
    path('django_function_view', django_function_view),
    path('django_class_view', DjangoView.as_view()),
]


# ------------------------------------------------------------------------------


@pytest.mark.urls(__name__)
class TestPatchFunctionViews():

    def setup(self):
        patching.patch()  # Ensure patching occurs!
        self.urlconf = importlib.import_module(__name__)
        self.resolver = get_resolver(self.urlconf)

    def test_django_function_views_are_patched_directly(self):
        match = self.resolver.resolve('/django_function_view')
        assert match.func != django_function_view  # should point to wrapper
        match.func.__qualname__.startswith('function_view_wrapper')
        assert match.func.__module__ == 'patching'

    def test_check_permissions_is_called(self):
        url = '/django_function_view'
        match = self.resolver.resolve(url)
        request = RequestFactory().get(url)

        with patch('patching.check_permissions') as mocked_check_permissions:
            response = match.func(request)
            assert response.status_code == 200
            assert mocked_check_permissions.called


@pytest.mark.urls(__name__)
class TestPatchClassViews():
    """
    Django method views are wrapped on the class directly.
    """

    def setup(self):
        patching.patch()  # Ensure patching occurs!
        self.urlconf = importlib.import_module(__name__)
        self.resolver = get_resolver(self.urlconf)

    def test_dispatch_is_not_wrapped(self):
        match = self.resolver.resolve('/django_class_view')
        assert match.func.__wrapped__.__name__ == 'dispatch'

    def test_methods_are_wrapped(self):
        match = self.resolver.resolve('/django_class_view')
        cls = match.func.view_class
        assert cls.get.__qualname__.startswith('class_view_wrapper')

    def test_check_permissions_is_called(self):
        url = '/django_class_view'
        match = self.resolver.resolve(url)
        request = RequestFactory().get(url)

        with patch('patching.check_permissions') as mocked_check_permissions:
            response = match.func(request)
            assert response.status_code == 200
            assert mocked_check_permissions.called
