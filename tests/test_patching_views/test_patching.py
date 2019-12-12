from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, rest_function_view
from .test_patching_django import urlpatterns as django_urlpatterns
from .test_patching_rest import urlpatterns as rest_urlpatterns
from patching import is_method_view, get_view_class


all_urlpatterns = django_urlpatterns + rest_urlpatterns


def test_is_method_view():
    # We know that only django_function_view is not a method
    # For REST every view is a method, including decorated functions.
    for pattern in all_urlpatterns:
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
