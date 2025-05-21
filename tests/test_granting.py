import pytest
from django.conf import settings
from django.contrib.auth.models import User

from rest_framework_roles.granting import is_self, anyof, allof
from rest_framework_roles import patching
from .fixtures import anon, user, admin, test_user1, test_user2, test_user3
from .utils import assert_allowed, assert_disallowed, UserSerializer


# -------------------------------- Recipe ---------------------------------


import rest_framework.routers
import rest_framework.permissions
import rest_framework.viewsets
import rest_framework as drf
from django.urls import path, include


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'list': {
            'test_user1': anyof(False, True),
            'test_user2': allof(True, True),
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

    def test_anyof(self, test_user1):
        assert_allowed(test_user1, get='/users/')
        
    def test_allof(self, test_user2):
        assert_allowed(test_user2, get='/users/')