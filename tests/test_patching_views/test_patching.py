from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory

from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, rest_function_view_undecorated
from .test_patching_rest import urlpatterns as rest_urlpatterns
from .test_patching_django import django_function_view_undecorated
from .test_patching_django import urlpatterns as django_urlpatterns
from rest_framework_roles.patching import is_callback_method, get_view_class

# NOTE: Do not patch in this module. It will double-patch and give an error.


urlpatterns = rest_urlpatterns + django_urlpatterns

def get_pattern(name):
    for pattern in urlpatterns:
        if name in str(pattern):
            return pattern


def test_is_callback_method():
    # We know that only django_function_view is not a method
    # For REST every view is a method, including decorated functions.
    # import rest_framework
    assert is_callback_method(get_pattern('django_class_view').callback)
    assert is_callback_method(get_pattern('rest_class_view').callback)
    assert is_callback_method(get_pattern('rest_class_viewset').callback)
    assert is_callback_method(get_pattern('list_model_mixin_admin_only').callback)


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view_undecorated).__qualname__ == 'WrappedAPIView'

    assert get_view_class(RestViewSet.as_view({'get': 'list'})) == RestViewSet
    assert get_view_class(RestViewSet.as_view({'get': 'custom_view'})) == RestViewSet