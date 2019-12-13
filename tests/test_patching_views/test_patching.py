import importlib
from unittest import mock

import pytest
from django.urls import get_resolver
from django.test import RequestFactory

from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, rest_function_view
from .test_patching_django import urlpatterns as django_urlpatterns
from .test_patching_rest import urlpatterns as rest_urlpatterns
from patching import is_method_view, get_view_class, patch, before_view


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


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view).__qualname__ == 'WrappedAPIView'

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


@pytest.mark.urls(__name__)
def test_before_view_patched_in_all_cases():
    """ before_view must always be called regardless how we define permissions """
    patch()


    # For Django functions it is patched directly at URL resolution level
    assert 'before_view' in str(get_pattern('django_function_view').callback)

    # For everything else the views are patched at the class level
    class_based_patterns = [
        get_pattern('django_class_view'),
        # get_pattern('rest_function_view'),
        # get_pattern('rest_class_view'),
        # get_pattern('rest_class_viewset'),
        # get_pattern('rest_class_viewset/custom_view'),
    ]
    for pattern in class_based_patterns:
        assert 'before_view' not in str(pattern.callback)
        cls = pattern.callback.view_class

        import IPython; IPython.embed(using=False)









    # import IPython; IPython.embed(using=False)
    # urlconf = importlib.import_module(__name__)
    # resolver = get_resolver(urlconf)
    #
    # match = resolver.resolve('/django_function_view')
    #
    #
    # match = self.resolver.resolve('/django_class_view')
    # cls = match.func.view_class
    # assert cls.get.__qualname__.startswith('class_view_wrapper')
