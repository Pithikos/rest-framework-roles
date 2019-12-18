import importlib
from unittest import mock

import pytest
from django.urls import get_resolver
from django.test import RequestFactory

from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, rest_function_view_decorated, rest_function_view_undecorated
from .test_patching_rest import urlpatterns as rest_urlpatterns
from .test_patching_django import django_function_view_decorated, django_function_view_undecorated
from .test_patching_django import urlpatterns as django_urlpatterns
from patching import is_method_view, get_view_class, patch, before_view, is_rest_function_view


urlpatterns = django_urlpatterns + rest_urlpatterns

urlconf = importlib.import_module(__name__)
patch(urlconf)
resolver = get_resolver(urlconf)


def get_pattern(name):
    for pattern in urlpatterns:
        if name in str(pattern):
            return pattern


def test_is_method_view():
    # We know that only django_function_view is not a method
    # For REST every view is a method, including decorated functions.
    for pattern in urlpatterns:
        if 'django_function_view' in str(pattern):
            assert not is_method_view(pattern.callback)
        else:
            assert is_method_view(pattern.callback)


def test_is_rest_function_view():
    assert is_rest_function_view(rest_function_view_decorated)
    assert is_rest_function_view(rest_function_view_undecorated)

    assert not is_rest_function_view(django_function_view_decorated)
    assert not is_rest_function_view(django_function_view_undecorated)
    assert not is_rest_function_view(RestAPIView.view_unpatched)
    assert not is_rest_function_view(RestAPIView.get)
    assert not is_rest_function_view(DjangoView.as_view())
    assert not is_rest_function_view(RestAPIView.as_view())


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view_decorated).__qualname__ == 'WrappedAPIView'
    assert get_view_class(rest_function_view_undecorated).__qualname__ == 'WrappedAPIView'

    assert get_view_class(RestViewSet.as_view({'get': 'list'})) == RestViewSet
    assert get_view_class(RestViewSet.as_view({'get': 'custom_view'})) == RestViewSet


def test_check_permissions_is_called_by_before_view():
    url = '/django_function_view_decorated'
    match = resolver.resolve(url)
    request = RequestFactory().get(url)
    with mock.patch('patching.check_permissions') as mocked_check_permissions:
        response = match.func(request)
        assert response.status_code == 200
        assert mocked_check_permissions.called
