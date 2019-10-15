import sys

from django.conf import settings
from django.utils.functional import empty

from .roles import is_creator, is_user, is_anon, is_admin, is_staff


def django_is_configured():
    return settings._wrapped is not empty


def _patch_rest_framework():
    from .views import PatchedAPIView
    sys.modules['rest_framework'].views.APIView = PatchedAPIView


# Ensure patching happens during the configuration of Django or after
if django_is_configured():
    _patch_rest_framework()
