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


def is_creator(view, request):
    obj = view.get_object()
    if hasattr(obj, 'creator'):
        return request.user == obj.creator
    return False


def is_user(view, request):
    return isinstance(request.user, get_user_model())


def is_anon(view, request):
    return request.user.is_anonymous


def is_admin(view, request):
    return request.user.is_superuser


def is_staff(view, request):
    return request.user.is_staff or is_admin(request)


# Roles must be classes implementing either has_role or has_object_role
ROLES = {
    'user': is_user,
    'anon': is_anon,
    'owner': is_creator,
    'admin': is_admin,
    'staff': is_staff,
}
