import pytest

from rest_framework_roles.parsing import validate_config, load_roles
from rest_framework_roles.roles import is_admin, is_anon


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


# ---------------------------------- Basic -------------------------------------


def test_load_roles_by_dotted_path():
    assert load_roles({'ROLES': VALID_ROLES_PATH})


def test_validate_config():
    validate_config({'ROLES': None})
    with pytest.raises(Exception):
        validate_config({'garbage': 'whatever'})  # unknown setting
