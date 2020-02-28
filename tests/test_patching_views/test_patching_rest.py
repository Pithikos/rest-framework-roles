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
from rest_framework_roles.decorators import allowed
from ..utils import UserSerializer, _func_name, is_preview_patched, is_predispatch_patched
from rest_framework_roles.roles import is_user


# -------------------------------- Setup app -----------------------------------


@allowed('admin')
@drf.decorators.api_view(['get', 'post'])
def rest_function_view_decorated(request):
    return HttpResponse(_func_name())


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


class RestAdminFallback(drf.generics.GenericAPIView):
    permission_classes = (drf.permissions.IsAdminUser,)
    @allowed('user')
    def get(self, request):
        return HttpResponse(_func_name())


class RestClassMixed(drf.mixins.ListModelMixin, drf.generics.GenericAPIView):
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


urlpatterns = [
    # Rest functions end up being methods to a class
    path('rest_function_view_decorated', rest_function_view_decorated),
    path('rest_function_view_undecorated', rest_function_view_undecorated),

    # Normal class
    path('rest_class_view', RestAPIView.as_view()),
    path('rest_admin_fallback', RestAdminFallback.as_view()),

    # Similar to functions
    path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),

    # Etc..
    path('rest_class_mixed', RestClassMixed.as_view()),
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
def test_function_views_patching(rest_resolver, client):
    # We simply ensure that check_permissions is called and don't dwell into how the
    # patching occurs

    with patch('rest_framework_roles.patching.check_permissions') as check_permissions:
        resp = client.get('/rest_function_view_decorated')
        assert resp.status_code != 404
        assert check_permissions.called

    with patch('rest_framework_roles.patching.check_permissions') as check_permissions:
        resp = client.get('/rest_function_view_undecorated')
        assert resp.status_code != 404
        assert not check_permissions.called


@pytest.mark.urls(__name__)
def test_class_views_specified_methods_patched(rest_resolver, client):
    # REST Framework essentially redirects classic Django views to a higher level
    # interface. e.g. self.get -> self.retrieve
    #
    # We need to ensure that only the specified views get patched and nothing more
    # for classes.
    match = rest_resolver.resolve('/rest_class_mixed')
    assert not is_preview_patched(match.func.cls.get)

    def _test_instance(self, request):
        assert self.get
        assert self.list
        assert not is_preview_patched(self.get)
        assert is_preview_patched(self.list)

    # We patch 'initial' since that is called inside the original dispatch
    # so gives us self after the pre-dispatch hook runs
    with patch.object(RestClassMixed, 'initial', new=_test_instance):
        resp = client.get('/rest_class_mixed')
        assert resp.status_code != 404


@pytest.mark.urls(__name__)
def test_class_instance_patched(db, rest_resolver, client):
    # We should not patch the class methods directly but the instances. This is since a class can
    # inherit for mixins and we don't want to end up having two classes sharing the same mixin
    # to behave the same.
    assert rest_resolver.resolve('/rest_class_mixed') != rest_resolver.resolve('/rest_class_mixed2')

    admin = User.objects.create(username='admin', is_superuser=True)
    client.force_authenticate(admin)
    resp = client.get('/rest_class_mixed')
    assert resp.status_code == 200
    resp = client.get('/rest_class_mixed2')
    assert resp.status_code == 403

    # ------------------------------------------------------------------

    def _test_instance(self, request):
        # 'get' and 'list' are the same at this point since as_view(),
        # populates the 'get' as a shortcut for 'list'.
        assert self.get
        assert self.list
        assert is_preview_patched(self.get)  # although not explicitly set perms
        assert is_preview_patched(self.list)
        return HttpResponse()

    # We patch 'initial' since that is called inside the original dispatch
    # so gives us self after the pre-dispatch hook runs
    with patch.object(RestClassModel, 'initial', new=_test_instance):
        client.get('/users/')

    assert not is_preview_patched(RestClassModel.list)


class TestCheckPermissionsFlow():
    """
    In REST we shuffle the check_permissions so that it occurs after our own
    check_permissions. This requires a few extra steps.
    """

    @pytest.mark.urls(__name__)
    def test_check_permissions_precedes_original_check_permissions(self, db, rest_resolver, client):
        """ We expect after patching to get"""

        # Anon gets caught by fallback (IsAdminUser)
        # 1. Stay anon
        # 2. Call the view
        # 3. Ensure fallback fires (since we didn't match the user role)
        resp = client.get('/rest_admin_fallback')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        # User does not get caught into the fallback
        # 1. Login
        # 2. Call the view
        # 3. Ensure we bypass the admin fallback
        user = User.objects.create(username='test')
        client.force_authenticate(user)
        resp = client.get('/rest_admin_fallback')
        assert resp.status_code == status.HTTP_200_OK
