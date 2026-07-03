from unittest import mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser

from .test_patching_django import DjangoView
from .test_patching_rest import RestAPIView, RestViewSet, RestClassModel, rest_function_view_undecorated
from .test_patching_rest import urlpatterns as rest_urlpatterns
from .test_patching_django import django_function_view_undecorated
from .test_patching_django import urlpatterns as django_urlpatterns
from rest_framework_roles.patching import is_callback_method, get_view_class
from rest_framework_roles import patching
from ..utils import assert_allowed, assert_disallowed


from django.contrib import admin
from django.urls import path, include

from rest_framework import routers


third_party_urlpatterns = [
    path("admin/", admin.site.urls),
]


urlpatterns = rest_urlpatterns + django_urlpatterns + third_party_urlpatterns

def get_pattern(name):
    for pattern in urlpatterns:
        if name in str(pattern):
            return pattern


def test_is_callback_method():
    # We know that only django_function_view is not a method
    # For REST every view is a method, including decorated functions.
    # import rest_framework
    assert is_callback_method(get_pattern('django_class_view').callback)
    assert is_callback_method(get_pattern('rest_class_view').callback)
    assert is_callback_method(get_pattern('rest_class_viewset').callback)
    assert is_callback_method(get_pattern('list_model_mixin_admin_only').callback)


def test_get_view_class():
    assert get_view_class(DjangoView.as_view()) == DjangoView
    assert get_view_class(RestAPIView.as_view()) == RestAPIView
    assert get_view_class(rest_function_view_undecorated).__qualname__ == 'WrappedAPIView'

    assert get_view_class(RestViewSet.as_view({'get': 'list'})) == RestViewSet
    assert get_view_class(RestViewSet.as_view({'get': 'custom_view'})) == RestViewSet


@pytest.mark.urls(__name__)
def test_not_interfere_with_third_party():
    patching.patch()
    urlconf = mock.MagicMock()
    urlconf.urlpatterns = third_party_urlpatterns
    patterns = patching.get_urlpatterns(urlconf)

    # Ensure not patched
    for pattern in patterns:
        assert '_rfr_wrapped' not in pattern.callback.__qualname__


@pytest.mark.urls(__name__)
class TestPatchIsIdempotent:
    """
    Regression tests: calling patch() more than once in the same process must be
    safe. Previously post_patch() resolved DEFAULT_EXCEPTION_CLASS from its own
    (already-resolved) output, so the 2nd call raised Misconfigured, and handlers
    got wrapped on top of wrappers (which could trip MAX_VIEW_REDIRECTION_DEPTH).
    """

    def test_calling_patch_twice_does_not_raise(self):
        patching.patch()
        patching.patch()  # used to raise Misconfigured("...must be a string")

    def test_exception_class_stays_a_resolved_exception(self):
        patching.patch()
        patching.patch()
        exc = patching.DEFAULT_EXCEPTION_CLASS
        assert isinstance(exc, type) and issubclass(exc, Exception), \
            f"Expected a resolved exception class, got {exc!r}"

    def test_handlers_are_not_re_wrapped(self):
        patching.patch()
        wrapped_once = RestClassModel.__dict__['retrieve']
        patching.patch()
        wrapped_twice = RestClassModel.__dict__['retrieve']
        assert wrapped_once is wrapped_twice, "handler was wrapped again on re-patch"

    def test_access_still_correct_after_repeated_patching(self, db):
        for _ in range(5):
            patching.patch()
        # No stacked wrappers -> normal allow/deny, not a 500 from too-deep checks.
        # RestClassModel.retrieve is admin-only.
        admin_user = User.objects.create(username='admin', is_superuser=True)
        assert_allowed(admin_user, get=f'/users/{admin_user.id}/')
        assert_disallowed(AnonymousUser(), get=f'/users/{admin_user.id}/')