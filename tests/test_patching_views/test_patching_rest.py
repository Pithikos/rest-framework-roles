import importlib
from unittest.mock import patch

import pytest
from django.urls import get_resolver
from django.contrib.auth.models import User
from django.urls import path, include
from django.http import HttpResponse
from rest_framework import permissions, viewsets, views, decorators, generics, mixins, routers
import rest_framework as drf
from rest_framework.test import APIClient

import patching
from decorators import allowed
from ..utils import UserSerializer, _func_name, is_patched
from ..fixtures import request_factory


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


class RestClassMixed(drf.mixins.RetrieveModelMixin, drf.generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'retrieve': {'admin': True}}
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class RestClassModel(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {
        'retrieve': {'admin': True},
        'create': {'admin': False},
        'list': {'admin': False},
    }

    # def check_permissions(self, request):
    #     import IPython; IPython.embed(using=False)
router = drf.routers.DefaultRouter()
router.register(r'users', RestClassModel, basename='user')


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_decorated', rest_function_view_decorated),
    path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    path('rest_class_view', RestAPIView.as_view()),

    # Similar to functions
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),

    # Etc..
    path('rest_class_mixed', RestClassMixed.as_view()),
    path('', include(router.urls)),
]

# ------------------------------------------------------------------------------


@pytest.fixture(scope='session')
def rest_resolver():
    urlconf = importlib.import_module(__name__)
    patching.patch(urlconf)
    resolver = get_resolver(urlconf)
    return resolver


def test_function_views_patched(rest_resolver):
    # Although REST Framework end up being methods, we treat them similarly
    # to Django vanilla views. This is due to although being methods, the meta-
    # programmatically generated classes are missing the function as method.
    match = rest_resolver.resolve('/rest_function_view_decorated')
    assert is_patched(match.func.cls.get)
    assert is_patched(match.func.cls.post)

    # Views used in urlpatterns but not explicitly given permissions..
    match = rest_resolver.resolve('/rest_function_view_undecorated')
    assert not is_patched(match.func.cls.get)
    assert not is_patched(match.func.cls.post)


def test_method_views_patched_with_directives_only(rest_resolver):
    match = rest_resolver.resolve('/rest_class_view')
    cls = match.func.view_class  # => Normal class with corresponding method
    assert not is_patched(cls.get)
    assert not is_patched(cls.view_unpatched)
    assert is_patched(cls.view_patched_by_view_permissions)

    assert is_patched(cls.view_patched_by_decorator)
    assert is_patched(cls.action_patched_by_decorator)

    match = rest_resolver.resolve('/rest_class_viewset')
    cls = match.func.cls  # NOTE THE DIFFERENCE: We use cls instead of view_class
    assert is_patched(cls.list)


def test_not_doublepatching_views(rest_resolver):
    # REST Framework essentially redirects classic Django views to a higher level
    # interface. e.g. self.get -> self.retrieve
    #
    # We need to ensure that only the specified views get patched and nothing more
    # for classes.
    match = rest_resolver.resolve('/rest_class_mixed')
    cls = match.func.view_class
    assert cls.get
    assert cls.retrieve
    assert not is_patched(cls.get)
    assert is_patched(cls.retrieve)


@pytest.mark.urls(__name__)
def test_instance(rest_resolver):
    # This test mainly demonstrates the underworkings of REST Framework and to
    # not consider the behaviour as a bug.
    def _test_instance(self, request):
        # 'get' and 'list' are the same at this point since as_view(),
        # populates the 'get' as a shortcut for 'list'.
        assert self.get
        assert self.list
        assert is_patched(self.get)  # although not explicitly set perms
        assert is_patched(self.list)
        assert self.list == self.get
        return HttpResponse()
    with patch.object(RestClassModel, 'dispatch', new=_test_instance): # any method will do
        APIClient().get('/users/')
