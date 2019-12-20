from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory

from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, rest_function_view_decorated, rest_function_view_undecorated
from .test_patching_rest import urlpatterns as rest_urlpatterns
from .test_patching_django import django_function_view_decorated, django_function_view_undecorated
from .test_patching_django import urlpatterns as django_urlpatterns
from patching import is_callback_method, get_view_class, before_view, is_callback_rest_function

# NOTE: Do not patch in this module. It will double-patch and give an error.


urlpatterns = django_urlpatterns + rest_urlpatterns

def get_pattern(name):
    for pattern in urlpatterns:
        if name in str(pattern):
            return pattern


def test_is_callback_method():
    # We know that only django_function_view is not a method
    # For REST every view is a method, including decorated functions.
    # import rest_framework
    assert not is_callback_method(get_pattern('django_function_view_decorated').callback)
    assert not is_callback_method(get_pattern('django_function_view_undecorated').callback)
    assert is_callback_method(get_pattern('django_class_view').callback)
    assert is_callback_method(get_pattern('rest_function_view_decorated').callback)
    assert is_callback_method(get_pattern('rest_function_view_undecorated').callback)
    assert is_callback_method(get_pattern('rest_class_view').callback)
    assert is_callback_method(get_pattern('rest_class_viewset').callback)
    assert is_callback_method(get_pattern('rest_class_mixed').callback)


def test_is_callback_rest_function():
    assert is_callback_rest_function(rest_function_view_decorated)
    assert is_callback_rest_function(rest_function_view_undecorated)

    assert not is_callback_rest_function(django_function_view_decorated)
    assert not is_callback_rest_function(django_function_view_undecorated)
    assert not is_callback_rest_function(RestAPIView.view_unpatched)
    assert not is_callback_rest_function(RestAPIView.get)
    assert not is_callback_rest_function(DjangoView.as_view())
    assert not is_callback_rest_function(RestAPIView.as_view())


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view_decorated).__qualname__ == 'WrappedAPIView'
    assert get_view_class(rest_function_view_undecorated).__qualname__ == 'WrappedAPIView'

    assert get_view_class(RestViewSet.as_view({'get': 'list'})) == RestViewSet
    assert get_view_class(RestViewSet.as_view({'get': 'custom_view'})) == RestViewSet


def test_check_permissions_is_called_by_before_view():
    view = lambda r: HttpResponse(status=200)
    request = RequestFactory().get('')
    patched_view = before_view(view, is_method=False)
    with mock.patch('patching.check_permissions') as mocked_check_permissions:
        response = patched_view(request)
        assert response.status_code == 200
        assert mocked_check_permissions.called
