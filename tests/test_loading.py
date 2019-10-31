import pytest

from ..parsing import load_config, load_roles, load_view_permissions
from ..roles import is_admin, is_anon


VALID_ROLES = {'admin': is_admin, 'anon': is_anon}
VALID_VIEW_PERMISSIONS = [
    {
        'view': 'someview',
        'permissions': {
            'admin': True,
            'anon': False,
        }
    }

]
REST_FRAMEWORK_ROLES = {}
VALID_ROLES_PATH = f'{__name__}.VALID_ROLES'
VALID_VIEW_PERMISSIONS_PATH = f'{__name__}.VALID_VIEW_PERMISSIONS'


def test_load_roles_by_dotted_path():
    assert load_roles({'roles': VALID_ROLES_PATH})


def test_load_view_permissions_by_dotted_path():
    assert load_view_permissions({'view_permissions': VALID_VIEW_PERMISSIONS_PATH})


def test_load_config():
    global REST_FRAMEWORK_ROLES
    REST_FRAMEWORK_ROLES = {
      'roles': VALID_ROLES_PATH,
      'view_permissions': VALID_VIEW_PERMISSIONS_PATH,
    }
    config = load_config(__name__)

    # Ensure paths are populated with the actual data
    assert config['roles'] == VALID_ROLES
    assert config['view_permissions'] == VALID_VIEW_PERMISSIONS


def test_load_config_missing_required_keys():
    global REST_FRAMEWORK_ROLES
    REST_FRAMEWORK_ROLES = {}
    with pytest.raises(Exception):
        load_config(__name__)
