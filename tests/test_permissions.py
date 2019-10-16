from unittest.mock import patch

from ..patching import is_django_configured
from .fixtures import admin, user, anon

# import IPython; IPython.embed(using=False)

import pytest
from django.contrib.auth.models import User
from django.test.utils import override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers, permissions

from ..roles import is_admin, is_user, is_anon
from ..permissions import is_self
# from ..parsing import create_lookup

"""
from django.core.management import call_command
from django.db import models
from django.test import TestCase

class TestModel(models.Model):
    data = models.FloatField()

    class Meta:
        app_label = 'myapp'

class LibraryTests(TestCase):
    def setUp(self):
        super(LibraryTests, self).setUp()
        models.register_models('myapp', TestModel)
        call_command('syncdb')
"""


def test_view_permissions_can_be_applied_directl_at_view():
    pass


def test_view_permissions_can_be_applied_at_settings():
    pass


BAD_REQUEST = 400
FORBIDDEN = 403
ALLOWED = 200


class TestUserAPI():

    def setUp(self):
        roles = {
            'admin': is_admin,
            'user': is_user,
            'anon': is_anon,
        }
        permissions = [{
          'view': 'rest_framework_roles.tests.test_permissions.UserViewSet',
          'permissions': {
            'user': {
                'retrieve': is_self,
            },
            'anon': {
                'create': True,
            },
            'admin': {
                'list': True,
            },
          }
        }]
        # TODO: Actually load the above in our system

    def test_only_admin_can_list_users(self, client, user, admin):
        client.force_login(admin)
        request = client.get('/users/')
        assert request.status_code == ALLOWED
        client.force_login(user)
        request = client.get('/users/')
        assert request.status_code == FORBIDDEN
        # anon
        request = client.get('/users/')
        assert request.status_code == FORBIDDEN


def test_view_redirectios_dont_omit_checks():
    pass
