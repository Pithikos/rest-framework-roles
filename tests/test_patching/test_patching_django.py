import importlib

import pytest
from django.urls import get_resolver

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
