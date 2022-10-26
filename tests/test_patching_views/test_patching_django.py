import importlib
from unittest.mock import patch

import pytest
import django
from django.urls import get_resolver
from django.contrib.auth.models import User
from django.urls import path
from django.http import HttpResponse

# from .urls import *
from rest_framework_roles import patching
from ..utils import _func_name, is_preview_patched


# -------------------------------- Setup app -----------------------------------


def django_function_view_undecorated(request):
    return HttpResponse(_func_name())


class DjangoView(django.views.generic.ListView):
    model = User
    view_permissions = {'get': {'admin': True}}

    def get(self, request):
        return HttpResponse(_func_name())

    def view_unpatched(self, request):
        return HttpResponse(_func_name())


urlpatterns = [
    path('django_class_view', DjangoView.as_view()),
]


# ------------------------------------------------------------------------------


@pytest.fixture(scope='session')
def django_resolver():
    urlconf = importlib.import_module(__name__)
    patching.patch(urlconf)
    resolver = get_resolver(urlconf)
    return resolver


@pytest.mark.urls(__name__)
def test_patching_instance_views(django_resolver, client):
    # Class methods should NEVER be patched due to different classes sharing inherited mixins
    match = django_resolver.resolve('/django_class_view')
    cls = match.func.view_class
    assert not is_preview_patched(cls.get)
    assert not is_preview_patched(cls.view_unpatched)

    # Ensure check_permissions called
    with patch('rest_framework_roles.permissions.check_permissions') as check_permissions:
        resp = client.get('/django_class_view')
        assert resp.status_code != 404
        assert check_permissions.called

    # TODO: Test to ensure instance view is patched to allow redirections between views
