from patching import is_method_view, get_view_class
from .urls import *


def test_is_method_view():
    for pattern in function_based_patterns.values():
        assert not is_method_view(pattern.callback)
    for pattern in class_based_patterns.values():
        assert is_method_view(pattern.callback)

    # Viewsets behave a bit differently
    for pattern in viewset_based_patterns.values():
        assert is_method_view(pattern.callback)


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view).__qualname__ == 'WrappedAPIView'

    assert get_view_class(RestViewSet.as_view({'get': 'list'})) == RestViewSet
    assert get_view_class(RestViewSet.as_view({'get': 'custom_view'})) == RestViewSet
