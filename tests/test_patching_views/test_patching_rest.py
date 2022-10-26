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
from rest_framework import status

from rest_framework_roles import patching
from ..utils import UserSerializer, _func_name, is_preview_patched
from rest_framework_roles.roles import is_user


# -------------------------------- Setup app -----------------------------------


@drf.decorators.api_view(['get', 'post'])
def rest_function_view_undecorated(request):
    return HttpResponse(_func_name())


class RestAPIView(drf.views.APIView):  # This is the mother class of all classes
    serializer_class = UserSerializer
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


class RestViewSet(drf.viewsets.ViewSet):
    view_permissions = {'list': {'admin': True}}
    def list(self, request):
        return HttpResponse(_func_name())


class RestClassMixed1(drf.mixins.ListModelMixin, drf.generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'list': {'admin': True}}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RestClassMixed2(drf.mixins.ListModelMixin, drf.generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'list': {'admin': False}}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RestClassMixedViewset(drf.mixins.ListModelMixin, drf.viewsets.GenericViewSet):
    """ Difference with GenericAPIView mixins, is that this can be used with router """
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'list': {'anon': True}}  # Super permissive since we test patching, not permissions


class RestClassModel(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {
        'retrieve': {'admin': True},
        'create': {'admin': False},
        'list': {'admin': False},
    }


router = drf.routers.DefaultRouter()
router.register(r'users', RestClassModel, basename='user')
router.register(r'listed_users', RestClassMixedViewset, basename='listed_users')


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    path('rest_class_view', RestAPIView.as_view()),

    # Similar to functions
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),

    # Etc..
    path('rest_class_mixed1', RestClassMixed1.as_view()),
    path('rest_class_mixed2', RestClassMixed2.as_view()),
    path('', include(router.urls)),
]

# ------------------------------------------------------------------------------


@pytest.fixture(scope='session')
def rest_resolver():
    urlconf = importlib.import_module(__name__)
    patching.patch(urlconf)
    resolver = get_resolver(urlconf)
    return resolver


@pytest.mark.urls(__name__)
def test_class_views_specified_methods_patched(rest_resolver, client):
    # REST Framework essentially redirects classic Django views to a higher level
    # interface. e.g. self.get -> self.retrieve
    #
    # We need to ensure that only the specified views get patched and nothing more
    # for classes.
    match = rest_resolver.resolve('/rest_class_mixed1')
    assert not is_preview_patched(match.func.cls.get)

    def _test_instance(self, request):
        assert self.get
        assert self.list
        assert not is_preview_patched(self.get)
        assert is_preview_patched(self.list)

    # We patch 'initial' since that is called inside the original dispatch
    # so gives us self after the pre-dispatch hook runs
    with patch.object(RestClassMixed1, 'initial', new=_test_instance):
        resp = client.get('/rest_class_mixed1')
        assert resp.status_code != 404


@pytest.mark.urls(__name__)
def test_class_method_not_patched(db, rest_resolver, client):
    """
    One or more class views can share the same mixin, hence we don't want to patch
    the class method but instead the methods in the instances.
    """
    assert rest_resolver.resolve('/rest_class_mixed1') != rest_resolver.resolve('/rest_class_mixed2')

    admin = User.objects.create(username='admin', is_superuser=True)
    client.force_authenticate(admin)
    resp = client.get('/rest_class_mixed1')
    assert resp.status_code == 200
    resp = client.get('/rest_class_mixed2')
    assert resp.status_code == 403
    resp = client.get('/rest_class_mixed1')
    assert resp.status_code == 200
    resp = client.get('/rest_class_mixed2')
    assert resp.status_code == 403

    # Ensure class method of viewsets or mixin not wrapped (aka patched)
    assert RestClassMixed1.get.__qualname__ == "RestClassMixed1.get"
    assert RestClassMixed2.get.__qualname__ == "RestClassMixed2.get"
    assert drf.mixins.ListModelMixin.list.__qualname__ == "ListModelMixin.list"


@pytest.mark.urls(__name__)
def test_calling_unmixed_verb(db, rest_resolver, client):
    """
    For a viewset that only allows certain HTTP verbs, 405 should be given back as expected
    """

    # Normal case
    response = client.get('/listed_users/')
    assert response.status_code == 200

    # Calling patch (which is not defined)
    response = client.patch('/listed_users/')
    assert response.status_code == 405