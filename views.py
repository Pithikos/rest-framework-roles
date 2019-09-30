from django.conf import settings
from rest_framework.views import APIView as OriginalAPIView

from .parsing import create_lookup


def view_path(view):
    return view.__module__ + '.' + view.__class__.__name__


class PatchedAPIView(OriginalAPIView):
    """ Patches permission checking functions so that we can check by role """

    view_permissions = create_lookup()

    def check_permissions(self, request):
        """ Called every time """
        try:
            checkers_by_action = self.view_permissions[view_path(self)]['general_checkers']
            checkers = checkers_by_action.get(self.action) or \
                       checkers_by_action.get('*') or \
                       []
        except KeyError:
            return OriginalAPIView.check_permissions(self, request)

        # At this point we have checkers that need to match
        for checker in checkers:
            if checker(request):
                return
        self.permission_denied(request, message='Permission denied')

    def check_object_permissions(self, request, obj):
        """ Called by get_object() """
        return OriginalAPIView.check_object_permissions(self, request, obj)
