from django.core.exceptions import PermissionDenied

from .decorators import expensive


PERMISSION_REGISTRY = {}


@expensive
def is_self(view, request):
    return request.user == view.get_object()


def check_permissions(request, view, *args, **kwargs):
    """
    Hook called at the right place to check role permissions
    """
    print(f'Check permissions for {request.user}')
    import IPython; IPython.embed(using=False)

    raise PermissionDenied('test')
