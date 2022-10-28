import importlib
from unittest.mock import patch

import pytest
from django.urls import get_resolver, set_urlconf
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse

from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.granting import is_self, anyof, allof
from rest_framework_roles.exceptions import Misconfigured
from rest_framework_roles import patching
from .fixtures import admin, user, anon
from .utils import assert_allowed, assert_disallowed, UserSerializer, get_response


# -------------------------------- Recipe ---------------------------------


import rest_framework.routers
import rest_framework.permissions
import rest_framework.viewsets
import rest_framework.decorators
import rest_framework as drf
from django.urls import path, include


ROLES = {
    'admin': is_admin,
    'user': is_user,
    'anon': is_anon,
}
settings.REST_FRAMEWORK_ROLES['ROLES'] = f"{__name__}.ROLES"


def not_updating_email(request, view):
    return 'email' not in request.data


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
        'update,partial_update': {
            'user': allof(is_self, not_updating_email),
            'admin': True,
        },
        'create': {'anon': True},
        'list': {'admin': True},
        'me': {'user': True},

        # Custom actions
        'only_user': {'user': True},
        'only_anon': {'anon': True},
        'only_admin': {'admin': True},
    }

    STATE = 0  # to check if state changes in some tests

    def redirect_view(self, request):
        if request.method == 'GET':
            return self.retrieve(request)
        elif request.method == 'PATCH':
            return self.partial_update(request)

    @drf.decorators.action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        return self.redirect_view(request)

    @drf.decorators.action(detail=False)
    def only_user(self, request):
        return HttpResponse()

    @drf.decorators.action(detail=False)
    def only_anon(self, request):
        return HttpResponse()

    @drf.decorators.action(detail=False)
    def only_admin(self, request):
        return HttpResponse()

    @drf.decorators.action(detail=False)
    def noexplicitpermission(self, request):
        UserViewSet.STATE += 1
        return HttpResponse()


class ListRedirectionsMixin():
    view_permissions = {
        'all_allowed': {'anon': True, 'user': True, 'admin': True},
        'only_admin_allowed': {'admin': True},
        'only_anon_allowed': {'anon': True},
    }

    @drf.decorators.action(methods=['get'], detail=False)
    def all_allowed(self, request):
        return self.list(request)

    @drf.decorators.action(methods=['get'], detail=False)
    def only_admin_allowed(self, request):
        return self.list(request)

    @drf.decorators.action(methods=['get'], detail=False)
    def only_anon_allowed(self, request):
        return self.list(request)


class RestrictedListViewSet(drf.viewsets.ModelViewSet, ListRedirectionsMixin):
    """Redirections trying to punch a hole"""
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'list': {'admin': True},
        **ListRedirectionsMixin.view_permissions,
    }


class PermissiveListViewSet(drf.viewsets.ModelViewSet, ListRedirectionsMixin):
    """Redirections trying to punch a hole"""
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'list': {'anon': True, 'user': True, 'admin': True},
        **ListRedirectionsMixin.view_permissions,
    }


class NoViewPermissionsNoPermissionClasses(drf.viewsets.ModelViewSet):
    """Used to ensure we always use least privileges"""
    serializer_class = UserSerializer
    queryset = User.objects.all()


class WithCustomPermissionClassesAllowAny(drf.viewsets.ModelViewSet):
    """Used to ensure views are protected properly even if user explicitly sets permission_classess"""
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [drf.permissions.AllowAny]


router = drf.routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'no_custom_permission_classes_no_view_permissions', NoViewPermissionsNoPermissionClasses, basename='no_custom_permission_classes_no_view_permissions')
router.register(r'with_custom_permission_classes_allowany', WithCustomPermissionClassesAllowAny, basename='with_custom_permission_classes_allowany')
router.register(r'only_admin_list', RestrictedListViewSet, basename='only_admin_list')
router.register(r'anyone_list', PermissiveListViewSet, basename='anyone_list')
urlpatterns = [path('', include(router.urls)),]


# ------------------------------------------------------------------------------


@pytest.mark.urls(__name__)
class TestUserAPI():

    def setup(self):
        patching.patch()

    def test_only_admin_can_list_users(self, user, anon, admin):
        assert_allowed(admin, get='/users/')
        assert_disallowed(anon, get='/users/')
        assert_disallowed(user, get='/users/')

    def test_user_can_retrieve_only_self(self, user, anon, admin):
        other_user = User.objects.create(username='otheruser')
        other_user_url = f'/users/{other_user.id}/'
        all_users_url = '/users/'

        # Positive cases
        assert_allowed(admin, get=f'/users/{admin.id}/')
        assert_allowed(other_user, get=other_user_url)
        assert_allowed(admin, get=other_user_url)  # admin is the only exception

        # Negative cases
        assert_disallowed(anon, get=other_user_url)  # fallback used
        assert_disallowed(user, get=other_user_url)

    def test_user_can_not_update_email(self, user, anon, admin):
        assert_allowed(user, patch=f'/users/{user.id}/', data={'username': 'newusername'})
        assert_disallowed(user, patch=f'/users/{user.id}/', data={'email': 'newemail@test.com'})
        assert_allowed(admin, patch=f'/users/{user.id}/', data={'email': 'newemail@test.com'})

    def test_only_anon_can_create(self, user, anon, admin):
        data = {'username': 'something', 'password': 'something'}
        assert_allowed(anon, post=f'/users/', data=data)
        assert_disallowed(user, post=f'/users/', data=data)
        assert_disallowed(admin, post=f'/users/', data=data)

    def test_view_redirectios_dont_omit_checks(self, user, anon, admin):
        assert_allowed(admin, get=f'/users/me/')
        assert_allowed(user, get=f'/users/me/')
        assert_disallowed(anon, get=f'/users/me/')

    def test_patched_action(self, user, anon, admin):
        assert_allowed(admin, get=f'/users/only_user/')  # admin is also a user
        assert_allowed(user, get=f'/users/only_user/')
        assert_disallowed(anon, get=f'/users/only_user/')

        assert_disallowed(admin, get=f'/users/only_anon/')
        assert_disallowed(user, get=f'/users/only_anon/')
        assert_allowed(anon, get=f'/users/only_anon/')


@pytest.mark.urls(__name__)
class TestLeastPrivilege():
    def setup(self):
        patching.patch()

    def test_missing_view_permission_yields_no_privilege(self, anon):
        assert_disallowed(anon, get=f'/users/noexplicitpermission/')

        # Ensure no state changed since no wrapped_view to call check_permissions
        assert UserViewSet.STATE == 0

    def test_vanilla_viewset_yields_no_privilege(self, anon):
        assert_disallowed(anon, get=f'/no_custom_permission_classes_no_view_permissions/')


TEST_CASES = [
    # URL,       user,    expected status
    ("/users/", "user", 403),
    ("/users/", "anon", 403),
    ("/users/", "admin", 200),
    ("/users/only_user/", "user", 200),
    ("/users/only_user/", "anon", 403),
    ("/users/only_user/", "admin", 200),  # since admin is a user
    ("/users/only_anon/", "user", 403),
    ("/users/only_anon/", "anon", 200),
    ("/users/only_anon/", "admin", 403),
    ("/users/only_admin/", "user", 403),
    ("/users/only_admin/", "anon", 403),
    ("/users/only_admin/", "admin", 200),
    ("/users/noexplicitpermission/", "user", 403),
    ("/users/noexplicitpermission/", "anon", 403),
    ("/users/noexplicitpermission/", "admin", 403),
    ("/no_custom_permission_classes_no_view_permissions/", "user", 403),
    ("/no_custom_permission_classes_no_view_permissions/", "anon", 403),
    ("/no_custom_permission_classes_no_view_permissions/", "admin", 403),
    ("/with_custom_permission_classes_allowany/", "user", 200),
    ("/with_custom_permission_classes_allowany/", "anon", 200),
    ("/with_custom_permission_classes_allowany/", "admin", 200),
    ("/zzzzzzzzzzzzzzzzzzzzzzzzzz/", "admin", 404),
]

@pytest.mark.urls(__name__)
class TestAccess():
    def setup(self):
        patching.patch()

    @pytest.mark.parametrize("url,usertype,expected_status", TEST_CASES)
    def test_check_role_permissions_called_max_once(self, url, usertype, expected_status, user, anon, admin):
        """
        Ensure check_permissions is never double-called
        """
        user = locals()[usertype]
        from rest_framework_roles.permissions import check_role_permissions as _original
        with patch('rest_framework_roles.permissions.check_role_permissions', wraps=_original) as mocked:
            assert get_response(user, get=url)
        assert mocked.call_count <= 1, f"check_permissions called {mocked.call_count} times"

    @pytest.mark.parametrize("url,usertype,expected_status", TEST_CASES)
    def test_right_permission_granted(self, url, usertype, expected_status, user, anon, admin):
        user = locals()[usertype]
        resp = get_response(user, get=url)
        assert resp.status_code == expected_status, f"'{usertype}' should get {expected_status}"

    def test_405(self):
        pass


@pytest.mark.urls(__name__)
class TestViewRedirection():
    """
    Ensure a redirection does not introduce a security hole
    """
    def setup(self):
        patching.patch()
    
    def test_restrictive_listing(self, user, anon, admin):
        """
        Ensure if 2 views used, the leasy privilege is in effect
        """

        # Default behaviour; listing
        assert_allowed(admin, get="/only_admin_list/")
        assert_disallowed(anon, get="/only_admin_list/")
        assert_disallowed(user, get="/only_admin_list/")

        # Least privilege determined by main view itself
        assert_allowed(admin, get="/only_admin_list/only_admin_allowed/")
        assert_disallowed(anon, get="/only_admin_list/only_admin_allowed/")
        assert_disallowed(user, get="/only_admin_list/only_admin_allowed/")

        assert_disallowed(admin, get="/only_admin_list/only_anon_allowed/")
        assert_disallowed(anon, get="/only_admin_list/only_anon_allowed/")
        assert_disallowed(user, get="/only_admin_list/only_anon_allowed/")

        assert_allowed(admin, get="/only_admin_list/all_allowed/")
        assert_disallowed(anon, get="/only_admin_list/all_allowed/")
        assert_disallowed(user, get="/only_admin_list/all_allowed/")

    def test_permissive_listing(self, user, anon, admin):
        assert_allowed(admin, get="/anyone_list/")
        assert_allowed(anon, get="/anyone_list/")
        assert_allowed(user, get="/anyone_list/")

        # Least privilege determined by redirection itself
        assert_allowed(admin, get="/anyone_list/only_admin_allowed/")
        assert_disallowed(anon, get="/anyone_list/only_admin_allowed/")
        assert_disallowed(user, get="/anyone_list/only_admin_allowed/")

        assert_disallowed(admin, get="/anyone_list/only_anon_allowed/")
        assert_allowed(anon, get="/anyone_list/only_anon_allowed/")
        assert_disallowed(user, get="/anyone_list/only_anon_allowed/")

        assert_allowed(admin, get="/anyone_list/all_allowed/")
        assert_allowed(anon, get="/anyone_list/all_allowed/")
        assert_allowed(user, get="/anyone_list/all_allowed/")


@pytest.mark.urls(__name__)
class TestWithCustomPermissionClassesAndViewPermissions:
    def test_raises_misconfiguration(self):
        """We don't allow both"""
        assert UserViewSet.view_permissions  # preassumption
        UserViewSet.permission_classes = [drf.permissions.AllowAny]
        with pytest.raises(Misconfigured):
            patching.patch()


@pytest.mark.urls(__name__)
class TestGroupedPermissions:
    def setup(self):
        patching.patch()

    def test_check_role_permissions_not_doublecalling(self, admin, user, anon):

        from rest_framework_roles.permissions import check_role_permissions as og_check_role_permissions
        from rest_framework_roles.permissions import _check_role_permissions as _og_check_role_permissions
        with patch('rest_framework_roles.permissions.check_role_permissions', wraps=og_check_role_permissions) as mocked_check_role_permissions:
            with patch('rest_framework_roles.permissions._check_role_permissions', wraps=_og_check_role_permissions) as _mocked_check_role_permissions:
                assert_allowed(user, patch=f'/users/{user.id}/', data={'username': 'newusername'})

        # check_permissions called twice due to the default update_partial -> update redirection
        assert mocked_check_role_permissions.call_count == 2

        # BUT the 3nd time we expect the checking to have been bypassed
        assert _mocked_check_role_permissions.call_count == 1