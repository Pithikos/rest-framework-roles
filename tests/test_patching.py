import importlib
from unittest.mock import patch, MagicMock, Mock, call

import pytest
from django.urls import get_resolver, set_urlconf
from django.conf import settings
from rest_framework.test import APIRequestFactory

from .utils import UserSerializer, _func_name
from .fixtures import admin, user, anon
import patching


# ------------------------------------------------------------------------------


from rest_framework import routers, permissions, viewsets, views, decorators, generics
import rest_framework as drf
from django.views.generic import ListView
import django
from django.contrib.auth.models import User
from django.urls import path, include
from django.http import HttpResponse


def django_function_view(request):
    return HttpResponse(_func_name())


@drf.decorators.api_view()
def rest_function_view(request):
    # This behaves exactly the same as if it was a method of APIView
    return HttpResponse(_func_name())


class DjangoView(django.views.generic.ListView):
    model = User

    def get(self, request):
        return HttpResponse(_func_name())

    def not_a_view(self, *args, **kwargs):
        # Not a view since not the standard get, post, etc.
        return HttpResponse(_func_name())


class RestAPIView(drf.views.APIView):  # This is the mother class of all classes
    serializer_class = UserSerializer
    permission_classes = (drf.permissions.AllowAny,)
    queryset = User.objects.all()

    def get(self, request):
        return HttpResponse(_func_name())

    def not_a_view(self, *args, **kwargs):
        # Not a view since not marked with decorator
        return HttpResponse(_func_name())


class RestViewSet(drf.viewsets.ViewSet):
    def list(self, request):
        return HttpResponse(_func_name())

    def custom_view(self, request):
        return HttpResponse(_func_name())

    # TODO: This is not tested atm
    @drf.decorators.action(detail=False, methods=['get'], url_name='custom_action', url_path='custom_action')
    def custom_action(self, request):
        return HttpResponse(_func_name())


urlpatterns = []
function_based_patterns = {
    '/django_function_view': path('django_function_view', django_function_view),
}
class_based_patterns = {
    '/rest_function_view': path('rest_function_view', rest_function_view),  # internally ends up being a method
    '/django_class_view': path('django_class_view', DjangoView.as_view()),
    '/rest_class_view': path('rest_class_view', RestAPIView.as_view()),
}
viewset_based_patterns = {
    '/rest_class_viewset': path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),
    '/rest_class_viewset/custom_view': path('rest_class_viewset/custom_view', RestViewSet.as_view({'get': 'custom_view'})),
    # NOTE: `custom_action` path is autopopulated by REST Framework
}
# TODO: Test with router + action

# ------------------------------------------------------------------------------


def test_is_method_view():
    for pattern in function_based_patterns.values():
        assert not patching.is_method_view(pattern.callback)
    for pattern in class_based_patterns.values():
        assert patching.is_method_view(pattern.callback)

    # Viewsets behave a bit differently
    for pattern in viewset_based_patterns.values():
        assert patching.is_method_view(pattern.callback)


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
    REST functions behave excactly the same as REST method videos. Internally
    they are attached to a WrappedAPI class.
    """

    def setup(self):
        global urlpatterns
        urlpatterns = class_based_patterns.values()
        patching.patch()  # Ensure patching occurs!
        self.urlconf = importlib.import_module(__name__)
        self.resolver = get_resolver(self.urlconf)

    def test_rest_function_views_are_not_patched_directly(self):
        """
        For class-based views, the callback is always the dispatch() method. We
        instead patch the views of the class that will be called by dispatch().
        """
        match = self.resolver.resolve('/rest_function_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
        match = self.resolver.resolve('/rest_class_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
        match = self.resolver.resolve('/django_class_view')
        assert match.func.__wrapped__.__name__ == 'dispatch'

    def test_method_views_patching(self, client, admin):
        """
        We expect the below order:

            dispatch -> get -> view wrapper -> view method
        """
        for url, view_name in (
            ('/rest_function_view', 'rest_function_view'),
            ('/django_class_view', 'get'),
            ('/rest_class_view', 'get'),
                                                            ):

            match = self.resolver.resolve(url)
            request = APIRequestFactory().get(url)
            cls = match.func.view_class
            inst = cls()

            calls = []
            def mark_called_dispatch(*args):
                calls.append('dispatch')
            def mark_called_view_wrapper(*args):
                calls.append('view_wrapper')

            # Keep track of order the functions are called
            with patch.object(cls, 'dispatch', wraps=inst.dispatch) as mock_dispatch:
                mock_dispatch.side_effect = mark_called_dispatch
                with patch('patching.before_view') as mock_before_view:
                    mock_before_view.side_effect = mark_called_view_wrapper
                    # TODO: Test view was called after the view_wrapper
                    response = match.func(request)
                    assert response.status_code == 200
                    assert response.content.decode() == view_name
                    assert calls == ['dispatch', 'view_wrapper']

    # def test_DjangoListView(self):
    #     """
    #     Classes are a bit special since the view wrappers need to be applied on
    #     every view, and not the class callable with essentially is the dispatch()
    #     method. Aka patching must occur for each view
    #     """
    #     # Without patching
    #     match = self.resolver.resolve('/DjangoListView')
    #
    # # def test_RestAPIView(self):
    # #     match = self.resolver.resolve('/RestAPIView')
    # #     # Nothing before the dispatcher should be patched
    # #     assert match.func.__module__ != 'patching'
    # #     assert match.func.__name__ == 'RestAPIView'
    # #     assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
    # #     # All method views should be patched
    # #     # TODO: Ensure patching occurs on the vies..
    # #     """
    # #     Patching class methods strategy
    # #         1. We know which classes to patch.
    # #         2. Patch all methods of classes (except known parent methods which are
    # #            definetely not views) with a view-checker decorator.
    # #            method. It should call before_view in that case.
    # #         3. The decorator should check if the caller function is the dispatch. If
    # #            it is, then this should be a view and we therefore call before_view(view, ..)
    # #     """
    #     # assert
    #     # import IPython; IPython.embed(using=False)


def test_user_is_populated_inside_wrapper():
    """
    There is a huge difference between Django and REST when it comes to order of
    user population.

    In Django request.user is a lazy object and can thus be fetched at any point.
    However in REST, it is not so that can be a problem.
    """
    pass
