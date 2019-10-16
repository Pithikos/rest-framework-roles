from rest_framework.test import APIClient
_client = APIClient()


def _is_valid_response(valid_statuses, user, get=None, post=None):
    """ Check return statuses """
    assert get or post
    if user.is_anonymous:
        _client.force_authenticate()
    else:
        _client.force_authenticate(user)
    if get:
        request = _client.get(get)
    else:
        request = _client.post(post)
    return request.status_code in valid_statuses


def assert_allowed(user, get=None, post=None):
    if not _is_valid_response((200, 201), user, get, post):
        raise AssertionError(f"'{user}' should be allowed but is forbidden")


def assert_disallowed(user, get=None, post=None):
    if not _is_valid_response((403,), user, get, post):
        raise AssertionError(f"'{user}' should be fobidden but is allowed")
