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
from .utils import assert_allowed, assert_disallowed
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

    def test_only_admin_can_list_users(self, client, user, anon, admin):
        assert_allowed(admin, get='/users/')
        assert_disallowed(user, get='/users/')
        assert_disallowed(anon, get='/users/')

    def test_user_can_retrieve_only_self(self, client, user, anon, admin):
        other_user = User.objects.create(username='mrother')
        other_user_url = f'/users/{other_user.id}/'
        all_users_url = '/users/'
        assert_allowed(admin, get=other_user_url)
        assert_disallowed(user, get=other_user_url)
        assert_disallowed(anon, get=other_user_url)
        assert_allowed(admin, get=f'/users/{admin.id}/')
        assert_allowed(user, get=f'/users/{user.id}/')

def test_view_redirectios_dont_omit_checks():
    pass
