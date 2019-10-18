# IMPORTANT: Don't load any modules outside the testcases


def test_patch():
    """
    Ensure patching occurs once Django settings are loaded (which happens at
    conftest for the testsuite)
    """
    # Unload modules
    import sys
    del sys.modules['rest_framework']
    del sys.modules['rest_framework_roles']

    # Simulate order of loading for Django when reading the INSTALLED_APPS
    import rest_framework
    import rest_framework_roles

    # Ensure APIView is patched
    from rest_framework.views import APIView
    assert APIView._patched


def test_matching_actions_are_monkeypatched():
    """
    It's important that role checking is happening just before the view.

    This is since there are cases where check_permissions does not run. For example
    in the case of one view calling another, the check_permissions will only
    run on the first view but not the second.
    """
    pass
