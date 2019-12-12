import importlib
from unittest.mock import patch
from unittest import mock

import pytest
from django.urls import get_resolver
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User
from django.urls import path
from django.http import HttpResponse
from rest_framework import permissions, viewsets, views, decorators
import rest_framework as drf

import patching
from ..utils import UserSerializer, _func_name, dummy_view


# -------------------------------- Setup app -----------------------------------


@drf.decorators.api_view()
def rest_function_view(request):
    # This behaves exactly the same as if it was a method of APIView
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


urlpatterns = [
    path('rest_function_view', rest_function_view),  # internally ends up being a method
    path('rest_class_view', RestAPIView.as_view()),
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),
    path('rest_class_viewset/custom_view', RestViewSet.as_view({'get': 'custom_view'}))
]

# ------------------------------------------------------------------------------


@pytest.mark.urls(__name__)
class TestPatchClassViews():
    """
    REST functions behave exactly the same as in REST class views. They become
    methods of the class WrappedAPI.
    """

    def setup(self):

        # Store a reference to the original check_permissions to make testing easier
        cls = drf.views.APIView
        self.original_check_permissions = cls.check_permissions
        assert self.original_check_permissions.__qualname__ == 'APIView.check_permissions'

        # Patch
        patching.patch()
        self.urlconf = importlib.import_module(__name__)
        self.resolver = get_resolver(self.urlconf)

        # Ensure we still have reference after patching
        match = self.resolver.resolve('/rest_class_view')
        cls = match.func.cls
        assert cls.check_permissions.__qualname__.startswith('check_permissions_wrapper')
        assert self.original_check_permissions.__qualname__ == 'APIView.check_permissions'

    def test_dispatch_is_not_patched(self):
        match = self.resolver.resolve('/rest_function_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
        match = self.resolver.resolve('/rest_class_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'

    def test_methods_are_not_patched_directly(self):
        # Note this is different behaviour than Django class methods
        match = self.resolver.resolve('/rest_class_view')
        cls = match.func.cls
        assert not cls.get.__qualname__.startswith('method_view_wrapper'), "Should not be wrapped!"
        assert not cls.get.__qualname__.startswith('function_view_wrapper')

    def test_check_permissions_is_patched(self):
        match = self.resolver.resolve('/rest_class_view')
        cls = match.func.cls
        assert cls.check_permissions.__qualname__.startswith('check_permissions_wrapper'), "Should be wrapped!"

    @patch('patching.check_permissions')
    def test_check_permissions_is_called(self, mocked_check_permissions):
        url = '/rest_class_view'
        match = self.resolver.resolve(url)
        request = APIRequestFactory().get(url)

        response = match.func(request)
        assert response.status_code == 200
        assert mocked_check_permissions.called

    @patch('patching.check_permissions')
    def test_initial_calls_our_wrapper_instead_of_original_check_permissions(self, mocked_check_permissions):
        """
        initial() normally calls the check_permissions(). We need to ensure that
        our wrapper is called first.
        """
        url = '/rest_class_view'
        match = self.resolver.resolve(url)
        request = APIRequestFactory().get(url)
        cls = match.func.view_class
        inst = cls()

        request = drf.request.Request(request)  # initial requires a drf Request
        inst.initial(request)
        assert mocked_check_permissions.called

    def test_wrapper_called_between_dispatch_and_view(self):
        url = '/rest_class_view'
        match = self.resolver.resolve(url)
        request = APIRequestFactory().get(url)
        cls = match.func.view_class
        inst = cls()

        # Ensure our check_permissions called before the original one
        with patch('patching.check_permissions') as mocked_check_permissions:
            with patch.object(cls, 'dispatch', wraps=inst.dispatch) as mocked_dispatch:
                with patch.object(cls, 'get', wraps=dummy_view) as mocked_get:

                    manager = mock.Mock()
                    manager.attach_mock(mocked_check_permissions, 'check_permissions')
                    manager.attach_mock(mocked_dispatch, 'dispatch')
                    manager.attach_mock(mocked_get, 'get')

                    response = match.func(request)

                    # Check order
                    assert manager.mock_calls[0] == mock.call.dispatch(request)
                    assert str(manager.mock_calls[1]).startswith('call.check_permissions(')
                    assert str(manager.mock_calls[-1]).startswith('call.get(')
