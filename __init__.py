import sys

from django.core.exceptions import ImproperlyConfigured

from .roles import is_creator, is_user, is_anon, is_admin, is_staff


def _patch_rest_framework():
    from .views import PatchedAPIView
    sys.modules['rest_framework'].views.APIView = PatchedAPIView


# Ensure patching happens during the configuration of Django or after
try:
    _patch_rest_framework()
except ImproperlyConfigured:
    pass
