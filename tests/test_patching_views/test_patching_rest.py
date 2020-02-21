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
from ..utils import UserSerializer, _func_name, is_patched
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
    assert cls.list
    assert not is_patched(cls.get)
    assert is_patched(cls.list)


@pytest.mark.urls(__name__)
def test_not_patching_inherited_class(rest_resolver, db):
    # There was a bug where two class models patching the same view, ended
    # up patching e.g. RetrieveModelMixin.retrieve instead of Class1.retrieve
    # and Class2.retrieve
    match1 = rest_resolver.resolve('/rest_class_mixed')
    match2 = rest_resolver.resolve('/rest_class_mixed2')
    assert match1 != match2

    client = APIClient()
    admin = User.objects.create(username='admin', is_superuser=True)
    client.force_authenticate(admin)

    resp = client.get('/rest_class_mixed')
    assert resp.status_code == 200

    resp = client.get('/rest_class_mixed2')
    assert resp.status_code == 403


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


class TestCheckPermissionsFlow():
    """
    In REST we shuffle the check_permissions so that it occurs after our own
    check_permissions. This requires a few extra steps.
    """

    def test_original_check_permissions_nullified(self, rest_resolver):
        m = rest_resolver.resolve('/rest_admin_fallback')
        assert m.func.view_class.check_permissions is patching.dummy_check_permissions


    @pytest.mark.urls(__name__)
    def test_check_permissions_precedes_original_check_permissions(self, db, rest_resolver):
        """ We expect after patching to get"""
        client = APIClient()

        # First ensure view_permissions populated correctly
        m = rest_resolver.resolve('/rest_admin_fallback')
        cls = m.func.view_class
        perms = cls.get._view_permissions
        assert perms == [(True, is_user)]

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
