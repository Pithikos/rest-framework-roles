import importlib
from unittest.mock import patch

import pytest
from django.urls import get_resolver
from django.test import RequestFactory

from .urls import *
import patching


urlpatterns = []


# ------------------------------------------------------------------------------


@pytest.mark.urls(__name__)
class TestPatchFunctionViews():

    def setup(self):
        global urlpatterns
        urlpatterns = function_based_patterns.values()
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
        global urlpatterns
        urlpatterns = class_based_patterns.values()
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
