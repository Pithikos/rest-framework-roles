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
