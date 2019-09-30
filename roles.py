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


def is_owner(request, obj):
    return request.user == obj.creator


def is_user(request):
    return isinstance(request.user, get_user_model())


def is_anon(request):
    return request.user.is_anonymous


def is_admin(request):
    return request.user.is_superuser


def is_staff(request):
    return request.user.is_staff


ROLES = {
    'user':  {'role_checker': is_user},
    'anon':  {'role_checker': is_anon},
    'owner': {'role_checker': is_owner, 'check_instance': True},
    'admin': {'role_checker': is_admin},
    'staff': {'role_checker': is_staff},
}
