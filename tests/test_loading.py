import pytest

from ..parsing import load_config


ROLES = {}
VIEW_PERMISSIONS = []
REST_FRAMEWORK_ROLES = {}


def test_load_config():
    global REST_FRAMEWORK_ROLES
    REST_FRAMEWORK_ROLES = {
      'roles': 'rest_framework_roles.tests.conftest.ROLES',
      'view_permissions': 'rest_framework_roles.tests.conftest.VIEW_PERMISSIONS',
    }
    assert load_config(__name__)


def test_load_config_missing_required_keys():
    global REST_FRAMEWORK_ROLES
    REST_FRAMEWORK_ROLES = {}
    with pytest.raises(Exception):
        load_config(__name__)
