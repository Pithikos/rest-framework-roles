import sys

from django.conf import settings
from django.utils.functional import empty


def is_django_configured():
    return settings._wrapped is not empty


def patch_rest_framework():
    from .views import PatchedAPIView
    sys.modules['rest_framework'].views.APIView = PatchedAPIView


def try_patch():
    # Ensure patching happens during the configuration of Django or after
    if is_django_configured():
        patch_rest_framework()
