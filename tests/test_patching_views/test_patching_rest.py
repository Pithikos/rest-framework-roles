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
        'view_patched_by_view_permissions': {
            'admin': True,
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
    view_permissions = {'list': {'admin': True}}
    def list(self, request):
        return HttpResponse(_func_name())


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_decorated', rest_function_view_decorated),
    path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    path('rest_class_view', RestAPIView.as_view()),

    # Similar to functions
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),
]

# ------------------------------------------------------------------------------


urlconf = importlib.import_module(__name__)
patching.patch(urlconf)
resolver = get_resolver(urlconf)


def test_function_views_patched():
    # Although REST Framework end up being methods, we treat them similarly
    # to Django vanilla views. This is due to although being methods, the meta-
    # programmatically generated classes are missing the function as method.
    match = resolver.resolve('/rest_function_view_decorated')
    assert is_patched(match.func.cls.get)
    assert is_patched(match.func.cls.post)

    # Views used in urlpatterns but not explicitly given permissions..
    match = resolver.resolve('/rest_function_view_undecorated')
    assert not is_patched(match.func.cls.get)
    assert not is_patched(match.func.cls.post)


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
