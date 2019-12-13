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
from decorators import allowed
from ..utils import UserSerializer, _func_name, dummy_view, is_patched


# -------------------------------- Setup app -----------------------------------


@allowed('admin')
@drf.decorators.api_view(['get', 'post'])
def rest_function_view_decorated(request):
    return HttpResponse(_func_namcclse())


@drf.decorators.api_view(['get', 'post'])
def rest_function_view_undecorated(request):
    return HttpResponse(_func_name())


class RestAPIView(drf.views.APIView):  # This is the mother class of all classes
    serializer_class = UserSerializer
    permission_classes = (drf.permissions.AllowAny,)
    queryset = User.objects.all()
    view_permissions = {
        'admin': {
            'view_patched_by_view_permissions': True,
        }
    }

    # This is the vanilla view - unpatched
    def get(self, request):
        return HttpResponse(_func_name())

    def view_unpatched(self, request):
        return HttpResponse(_func_name())

    def view_patched_by_view_permissions(self, request):
        return HttpResponse(_func_name())

    @allowed('admin')
    def view_patched_by_decorator(self, request):
        return HttpResponse(_func_name())

    @allowed('admin')
    @drf.decorators.action(detail=False, methods=['get'])
    def action_patched_by_decorator(self, request):
        return HttpResponse(_func_name())


class RestViewSet(drf.viewsets.ViewSet):
    view_permissions = {'admin': {'list': True}}
    def list(self, request):
        return HttpResponse(_func_name())


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_decorated', rest_function_view_decorated),
    # path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    # path('rest_class_view', RestAPIView.as_view()),

    # Similar to functions
    # path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),
]

# ------------------------------------------------------------------------------


urlconf = importlib.import_module(__name__)
patching.patch(urlconf)
resolver = get_resolver(urlconf)

#
# def test_function_views_patched_regardless_of_directives():
#     # Normally we patch only views that are targeted by directives (e.g. decorators).
#     # Vanilla Django function views are the exception, and are patched directly
#     # regardless, in order to simplify things.
#     match = resolver.resolve('/django_function_view_decorated')
#     assert is_patched(match.func)
#     match = resolver.resolve('/django_function_view_undecorated')
#     assert is_patched(match.func)

def test_function_views_patched():
    # Although REST Framework end up being methods, we treat them similarly
    # to Django vanilla views. This is due to although being methods, the meta-
    # programmatically generated classes are missing the function as method.
    match = resolver.resolve('/rest_function_view_decorated')
    assert is_patched(match.func)
    # TODO: Check has view_permissions
    # TODO: Check patched with before_view
    # match = resolver.resolve('/rest_function_view_undecorated')
    # assert is_patched(match.func)


def test_method_views_patched_with_directives_only():
    match = resolver.resolve('/rest_class_view')
    cls = match.func.view_class  # => Normal class with corresponding method
    assert not is_patched(cls.get)
    assert not is_patched(cls.view_unpatched)
    assert is_patched(cls.view_patched_by_view_permissions)
    assert is_patched(cls.view_patched_by_decorator)
    assert is_patched(cls.action_patched_by_decorator)

    match = resolver.resolve('/rest_class_viewset')
    cls = match.func.cls  # NOTE THE DIFFERENCE: We use cls instead of view_class
    assert is_patched(cls.list)


# @pytest.mark.urls(__name__)
# class TestPatchClassViews():
#     """
#     REST functions behave exactly the same as in REST class views. They become
#     methods of the class WrappedAPI.
#     """
#
#     def setup(self):
#
#         # Store a reference to the original check_permissions to make testing easier
#         cls = drf.views.APIView
#         self.original_check_permissions = cls.check_permissions
#         assert self.original_check_permissions.__qualname__ == 'APIView.check_permissions'
#
#         # Patch
#         patching.patch()
#         self.urlconf = importlib.import_module(__name__)
#         self.resolver = get_resolver(self.urlconf)
#
#         # Ensure we still have reference after patching
#         match = self.resolver.resolve('/rest_class_view')
#         cls = match.func.cls
#         assert cls.check_permissions.__qualname__.startswith('check_permissions_wrapper')
#         assert self.original_check_permissions.__qualname__ == 'APIView.check_permissions'
#
#     def test_dispatch_is_not_patched(self):
#         match = self.resolver.resolve('/rest_function_view')
#         assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
#         match = self.resolver.resolve('/rest_class_view')
#         assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
#
#     def test_methods_are_not_patched_directly(self):
#         # Note this is different behaviour than Django class methods
#         match = self.resolver.resolve('/rest_class_view')
#         cls = match.func.cls
#         assert not cls.get.__qualname__.startswith('method_view_wrapper'), "Should not be wrapped!"
#         assert not cls.get.__qualname__.startswith('function_view_wrapper')
#
#     def test_check_permissions_is_patched(self):
#         match = self.resolver.resolve('/rest_class_view')
#         cls = match.func.cls
#         assert cls.check_permissions.__qualname__.startswith('check_permissions_wrapper'), "Should be wrapped!"
#
#     @patch('patching.check_permissions')
#     def test_check_permissions_is_called(self, mocked_check_permissions):
#         url = '/rest_class_view'
#         match = self.resolver.resolve(url)
#         request = APIRequestFactory().get(url)
#
#         response = match.func(request)
#         assert response.status_code == 200
#         assert mocked_check_permissions.called
#
#     @patch('patching.check_permissions')
#     def test_initial_calls_our_wrapper_instead_of_original_check_permissions(self, mocked_check_permissions):
#         """
#         initial() normally calls the check_permissions(). We need to ensure that
#         our wrapper is called first.
#         """
#         url = '/rest_class_view'
#         match = self.resolver.resolve(url)
#         request = APIRequestFactory().get(url)
#         cls = match.func.view_class
#         inst = cls()
#
#         request = drf.request.Request(request)  # initial requires a drf Request
#         inst.initial(request)
#         assert mocked_check_permissions.called
#
#     def test_wrapper_called_between_dispatch_and_view(self):
#         url = '/rest_class_view'
#         match = self.resolver.resolve(url)
#         request = APIRequestFactory().get(url)
#         cls = match.func.view_class
#         inst = cls()
#
#         # Ensure our check_permissions called before the original one
#         with patch('patching.check_permissions') as mocked_check_permissions:
#             with patch.object(cls, 'dispatch', wraps=inst.dispatch) as mocked_dispatch:
#                 with patch.object(cls, 'get', wraps=dummy_view) as mocked_get:
#
#                     manager = mock.Mock()
#                     manager.attach_mock(mocked_check_permissions, 'check_permissions')
#                     manager.attach_mock(mocked_dispatch, 'dispatch')
#                     manager.attach_mock(mocked_get, 'get')
#
#                     response = match.func(request)
#
#                     # Check order
#                     assert manager.mock_calls[0] == mock.call.dispatch(request)
#                     assert str(manager.mock_calls[1]).startswith('call.check_permissions(')
#                     assert str(manager.mock_calls[-1]).startswith('call.get(')
