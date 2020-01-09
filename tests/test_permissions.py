import importlib

import pytest
from django.urls import get_resolver, set_urlconf
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase  # needed for override_settings to work

from ..roles import is_admin, is_user, is_anon
from ..permissions import is_self
import patching
from .fixtures import admin, user, anon
from .utils import assert_allowed, assert_disallowed, UserSerializer


# -------------------------------- Recipe --------------------------------------

import rest_framework.routers
import rest_framework.permissions
import rest_framework.viewsets
import rest_framework as drf
from django.urls import path, include


ROLES = {
    'admin': is_admin,
    'user': is_user,
    'anon': is_anon,
}
settings.REST_FRAMEWORK_ROLES['roles'] = f"{__name__}.ROLES"


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = (drf.permissions.IsAdminUser,)  # this will act as fallback

    view_permissions = {
        'retrieve': {'user': is_self},
        'create': {'anon': True},
        'list': {'admin': True},
    }

    # def check_permissions(self, request):
    #     print('CHECK_PERMISSIONS')
    #     import IPython; IPython.embed(using=False)



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
        other_user = User.objects.create(username='mrother')
        other_user_url = f'/users/{other_user.id}/'
        all_users_url = '/users/'

        # Admin can retrieve all since IsAdmin is the fallback..
        # import ipdb; ipdb.set_trace()
        # de
        assert_allowed(admin, get=other_user_url)
        # TODO: Figure out when 'get' is populated.
        # assert_allowed(admin, get=f'/users/{admin.id}/')
        #
        # assert_disallowed(anon, get=other_user_url)
        # assert_disallowed(user, get=other_user_url)

    def test_only_anon_can_create(self, user, anon, admin):
        pass


def test_view_redirectios_dont_omit_checks():
    pass
