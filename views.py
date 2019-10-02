import inspect

from django.conf import settings
from rest_framework.views import APIView as OriginalAPIView

from .parsing import get_lookup, load_roles


VIEW_PERMISSIONS = get_lookup()


def view_path(view):
    return view.__module__ + '.' + view.__class__.__name__


def view_method_wrapper(view, func):
    """ Wraps every specified method """
    def wrapped(request, *args, **kwargs):
        action = func.__name__
        permissions = VIEW_PERMISSIONS[view_path(view)][action]

        # Evaluate permissions
        for granted, role_checker in permissions:
            if type(granted) is not bool:
                granted = granted(view, request)

            if granted and role_checker(view, request):
                return func(request, *args, **kwargs)
            if not granted and role_checker(view, request):
                return view.permission_denied(request, message='Permission denied')

    return wrapped


class PatchedAPIView(OriginalAPIView):
    """ Patches permission checking functions so that we can check by role """

    def __init__(self, *args, **kwargs):
        parent = super(OriginalAPIView, self)
        parent.__init__(*args, **kwargs)

        try:
            actions_lookup = VIEW_PERMISSIONS[view_path(self)]
        except KeyError:
            return None

        # Monkey-patch child's methods with a wrapper
        for action, checkers in actions_lookup.items():
            if not hasattr(self, action):
                continue
            original_func = getattr(self, action)
            setattr(self, action, view_method_wrapper(self, original_func))
