REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles)


Role-based permissions for Django and Django REST Framework.

  - Data-driven declarative permissions decoupled from views and models.
  - Implementation agnostic. Roles can utilize the database (like in Django) or be just a dict or anything you want.
  - Support for Django and REST Framework - working with class-based and function-based views.
  - Easy gradual integration with existing Django REST Framework projects.
  - Permissions are applied on a view-basis so redirections don't introduce security holes.


Install
-------

Install

    pip install rest_framework_roles


settings.py
```python
INSTALLED_APPS = {
    ..
    'rest_framework',
    'rest_framework_roles',  # Must be after rest_framework
}

REST_FRAMEWORK_ROLES = {
  'roles': 'myproject.roles.ROLES',
}

REST_FRAMEWORK = {
  ..
  'permission_classes': [],  # This ensures that by default noone is allowed access
  ..
}
```

roles.py
```python
from rest_framework_roles.roles import is_user, is_anon, is_admin


ROLES = {
    'admin': is_admin,
    'user': is_user,
    'anon': is_anon,
}
```

> You can create your own role checkers for custom roles. Each checker is a simple function that
takes `request` and `view` as arguments.


REST Framework example
-------------------------------

Permissions can be set either with the decorators **@allowed**, **@disallowed** or **view_permissions**. Permission is granted for any matching role. In case of no matching role, REST Framework's `permission_classes` is used as fallback.

> Views not explicitly set any permissions will simply fall to their default behaviour. This ensures smooth
integration with existing projects.


views.py
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework_roles.permissions import is_self


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
        'create': {'anon': True},
        'list': {'admin': True},
    }

    @allowed('admin', 'user')
    @action(detail=False, methods=['get'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        return self.retrieve(request)
```

> Note the permission for 'retrieve'. We need to include an explicit permission for 'admin' or else the admin user
will only be able to retrieve himself (matching the user role).


Advanced example
----------------

Sometimes you want to deal with more complex scenarios. Still this is way simpler than using `permission_classes` or similar as demonstrated below.

```python
from rest_framework_roles.permissions import is_self
from rest_framework_roles import roles


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {
        'retrieve': {'user': is_self},
        'update': {'user': is_self, 'admin': True},
        'create': {'anon': True},
        'list': {'admin': True},
        'me': {'user': True},
    }

    def update(self, request, **kwargs):
        # Allow only admin to change user's username
        if 'username' in request.data and not roles.is_admin(request, self):
            raise PermissionDenied('Only admin can change username')
        return super().update(request, **kwargs)

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        if request.method == 'GET':
            return self.retrieve(request)
        elif request.method == 'PATCH':
            return self.partial_update(request)
```

In this example:
  1. User can retrieve himself.
  2. User or admin can update himself, but 'username' is only allowed to be updated by admin.
  3. Only anonymous can create a user account.
  4. Action 'me' can be used for both retrieval and partial update.
