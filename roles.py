import importlib

from django.conf import settings


USER_MODEL = None


def load_user_model():
    pkgpath = '.'.join(settings.AUTH_USER_MODEL.split('.')[:-1])
    modelname = settings.AUTH_USER_MODEL.split('.')[-1]
    modelsmod = importlib.import_module(pkgpath + '.models')
    return getattr(modelsmod, modelname)


def get_user_model():
    # Get User model
    global USER_MODEL
    if USER_MODEL:
        return USER_MODEL
    USER_MODEL = load_user_model()
    return USER_MODEL


class Role():
    def __init__(self):
        if not (hasattr(self, 'has_role') ^ hasattr(self, 'has_object_role')):
            raise Exception("You must implement either 'has_role' or 'has_object_role'")


class OwnerRole(Role):
    def has_object_role(self, request, obj):
        return request.user == obj.creator


class UserRole(Role):
    def has_role(self, request):
        return isinstance(request.user, get_user_model())


class AnonRole(Role):
    def has_role(self, request):
        return request.user.is_anonymous


class AdminRole(Role):
    def has_role(self, request):
        return request.user.is_superuser


class StaffRole(Role):
    def has_role(self, request):
        return request.user.is_staff or is_admin(request)


# Roles must be classes implementing either has_role or has_object_role
ROLES = {
    'user': UserRole,
    'anon': AnonRole,
    'owner': OwnerRole,
    'admin': AdminRole,
    'staff': StaffRole,
}
