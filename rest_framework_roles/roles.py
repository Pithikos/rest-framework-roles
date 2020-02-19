from django.contrib.auth import get_user_model


def is_user(request, view):
    return isinstance(request.user, get_user_model())


def is_anon(request, view):
    return request.user.is_anonymous


def is_admin(request, view):
    return request.user.is_superuser


def is_staff(request, view):
    return request.user.is_staff or is_admin(request)


# Roles must be classes implementing either has_role or has_object_role
ROLES = {
    'user': is_user,
    'anon': is_anon,
    'admin': is_admin,
    'staff': is_staff,
}
