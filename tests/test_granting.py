import pytest
from django.conf import settings
from django.contrib.auth.models import User

from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.granting import is_self, anyof, allof
from rest_framework_roles import patching
from .fixtures import anon, user, admin
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
settings.REST_FRAMEWORK_ROLES['ROLES'] = f"{__name__}.ROLES"


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'list': {
            'user': anyof(False, True),
            'admin': allof(True, True),
        }
    }


router = drf.routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = [
    path('', include(router.urls)),
]


@pytest.mark.urls(__name__)
class TestUserAPI():

    def setup(self):
        patching.patch()

    def test_anyof(self, user, anon, admin):
        assert_allowed(user, get='/users/')
        
    def test_allof(self, user, anon, admin):
        assert_allowed(admin, get='/users/')