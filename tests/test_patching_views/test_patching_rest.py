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


# class SimpleRedirection(drf.views.APIView):


class RestViewSet(drf.viewsets.ViewSet):
    view_permissions = {'list': {'admin': True}}
    def list(self, request):
        return HttpResponse(_func_name())


class ListModelMixinAdminOnly(drf.mixins.ListModelMixin, drf.generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'list,get': {'admin': True}}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ListModelMixinNoone(drf.mixins.ListModelMixin, drf.generics.GenericAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {'list,get': {}}

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class ListModelMixinAnonOnly(drf.mixins.ListModelMixin, drf.viewsets.GenericViewSet):
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
router.register(r'list_model_mixin_anon_only', ListModelMixinAnonOnly, basename='list_model_mixin_anon_only')


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    path('rest_class_view', RestAPIView.as_view()),

    # Similar to functions
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),

    # Etc..
    path('list_model_mixin_admin_only', ListModelMixinAdminOnly.as_view()),
    path('list_model_mixin_noone', ListModelMixinNoone.as_view()),
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
def test_class_method_not_patched(db, rest_resolver, client):
    """
    One or more class views can share the same mixin, hence we don't want to patch
    the class method but instead the methods in the instances.
    """
    assert rest_resolver.resolve('/list_model_mixin_admin_only') != rest_resolver.resolve('/list_model_mixin_noone')

    admin = User.objects.create(username='admin', is_superuser=True)
    client.force_authenticate(admin)
    resp = client.get('/list_model_mixin_admin_only')
    assert resp.status_code == 200
    resp = client.get('/list_model_mixin_noone')
    assert resp.status_code == 403
    resp = client.get('/list_model_mixin_admin_only')
    assert resp.status_code == 200
    resp = client.get('/list_model_mixin_noone')
    assert resp.status_code == 403

    # Ensure we patch the inherited mixin instead the mixin itself
    assert not "wrapped" in drf.mixins.ListModelMixin.list.__qualname__


@pytest.mark.urls(__name__)
def test_calling_unmixed_verb(db, rest_resolver, client):
    """
    For a viewset that only allows certain HTTP verbs, 405 should be given back as expected
    """

    # Normal case
    response = client.get('/list_model_mixin_anon_only/')
    assert response.status_code == 200

    # Calling patch (which is not defined)
    response = client.patch('/list_model_mixin_anon_only/')
    assert response.status_code == 405