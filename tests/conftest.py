from os.path import dirname, abspath
import sys

import django
from django.conf import settings
from rest_framework_roles.roles import is_admin, is_user

ROLES = {
    'admin': is_admin,
    'user': is_user,
}
VIEW_PERMISSIONS = []
REST_FRAMEWORK_ROLES = {
  'roles': 'rest_framework_roles.tests.conftest.ROLES',
  'view_permissions': 'rest_framework_roles.tests.conftest.VIEW_PERMISSIONS',
}


urlpatterns = []  # Used only to avoid errors before we override ROOT_URLCONF in
                  # our test cases


def pytest_configure(config):
    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        REST_FRAMEWORK_ROLES=REST_FRAMEWORK_ROLES,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        STATIC_URL='/static/',
        ROOT_URLCONF=__name__,
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    "debug": True,  # We want template errors to raise
                }
            },
        ],
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'rest_framework',
            'rest_framework_roles',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
    )

    # Add project and test root to path
    sys.path.insert(0, dirname(dirname(abspath(__file__))))
    sys.path.insert(0, dirname(abspath(__file__)))
