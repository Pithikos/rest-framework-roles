import importlib

import pytest
from django.urls import get_resolver, set_urlconf
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse

from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.granting import is_self, anyof, allof
from rest_framework_roles import patching
from .fixtures import admin, user, anon
from .utils import assert_allowed, assert_disallowed, UserSerializer


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
settings.REST_FRAMEWORK_ROLES['roles'] = f"{__name__}.ROLES"


def not_updating_email(request, view):
    return 'email' not in request.data


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
        'partial_update': {
            'user': allof(is_self, not_updating_email),
            'admin': True,
        },
        'create': {'anon': True},
        'list': {'admin': True},
        'me': {'user': True},

        # Custom actions
        'only_user': {'user': True},
        'only_anon': {'anon': True},
    }

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
    def undecorated(self, request):
        return HttpResponse()

router = drf.routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = [
    path('', include(router.urls)),
]


# ------------------------------------------------------------------------------


def test_view_permissions_can_be_applied_directl_at_view():
    pass


def test_view_permissions_can_be_applied_at_settings():
    pass


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
