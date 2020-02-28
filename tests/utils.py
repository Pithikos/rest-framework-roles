import inspect

from django.contrib.auth.models import User
from django.http import HttpResponse
from rest_framework import serializers, permissions, viewsets
from rest_framework.test import APIClient
_client = APIClient()


def _func_name():
    """ Place inside a function to get the function's name """
    stack = inspect.stack()
    return stack[1][3]


def dummy_view(request):
    return HttpResponse()


def get_response(user, get=None, post=None, patch=None, data=None):
    """ Check return statuses """
    assert get or post or patch
    if user.is_anonymous:
        _client.force_authenticate()
    else:
        _client.force_authenticate(user)
    if get:
        return _client.get(get)
    elif post:
        return _client.post(post, data)
    elif patch:
        return _client.patch(patch, data)


def assert_allowed(user, get=None, post=None, patch=None, data=None, expected_status=(200, 201)):
    response = get_response(user, get, post, patch, data)
    if response.status_code not in expected_status:
        raise AssertionError(f"'{user}' should be allowed. Got {response.status_code} - '{response.content.decode()}'")


def assert_disallowed(user, get=None, post=None, patch=None, data=None, expected_status=(403,)):
    response = get_response(user, get, post, patch, data)
    if response.status_code not in expected_status:
        raise AssertionError(f"'{user}' should not be allowed. Got {response.status_code} - '{response.content.decode()}'")


def is_patched(fn):
    return 'before_view' in str(fn)


def is_predispatch_patched(fn):
    return 'before_dispatch' in str(fn)


def has_view_permissions(fn):
    return hasattr(fn, 'view_permissions')


# ------------------------------------------------------------------------------


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class BaseUserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)
    queryset = User.objects.all()
