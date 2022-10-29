import importlib
from unittest.mock import MagicMock, patch

import pytest
from django.urls import get_resolver, set_urlconf
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse

from rest_framework_roles.exceptions import Misconfigured
from rest_framework_roles.roles import is_admin, is_user, is_anon
from rest_framework_roles.granting import is_self, anyof, allof
from rest_framework_roles import patching
from .fixtures import admin, user, anon
import utils


# -------------------------------- Recipe ---------------------------------


import rest_framework.routers
import rest_framework.permissions
import rest_framework.viewsets
import rest_framework.decorators
import rest_framework as drf
from django.urls import path, include


class UserViewSet(drf.viewsets.ModelViewSet):
    serializer_class = utils.UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'list': {'admin': True},
        'retrieve': {'user': is_self}
    }


router = drf.routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
urlpatterns = [
    path('', include(router.urls)),
]


@pytest.mark.urls(__name__)
class TestRoleCheckers():

    def setup(self):
        self.is_admin = MagicMock()
        self.is_user = MagicMock()
        ROLES = {
            'admin': self.is_admin,
            'user': self.is_user,
        }
        urlconf = MagicMock()
        urlconf.urlpatterns = urlpatterns
        patching.patch(urlconf, ROLES)

    def test_view_instance_passed(self, user, anon, admin):
        """
        Ensure view instance instead of handler passed
        """
        assert not self.is_admin.called
        utils.get_response(admin, get='/users/')
        assert self.is_admin.called

        args, kwargs = self.is_admin.call_args
        request, view = args
        assert isinstance(view, UserViewSet)