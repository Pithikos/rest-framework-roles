REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles)


Role-based permissions for Django and Django REST Framework.

  - Data-driven declarative permissions decoupled from views and models.
  - Roles are implementation agnostic. You can utilize the database or a dict or anything in between.
  - Role checking can easily be optimized by simply annotating with a cost.
  - Permissions applied on a view-basis ensuring redirections don't introduce security holes.
  - Support for Django and REST Framework - working with class-based and function-based views.
  - Easy gradual integration with existing Django REST Framework projects.


Install
-------

Install

    pip install rest-framework-roles


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

Permissions can be set either with the decorators **@allowed**, **@disallowed** or **view_permissions**. Permissions
are checked for all matching roles at runtime. In case of no matching role, REST Framework's `permission_classes` is
used as fallback.

> Note that views need to explictly be set any permissions either via decorators or *view_permissions*. Otherwise those
views will not go through the permission checking. This is intended behaviour since it allows easier gradual integration
when other 3rd party libraries are used.


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

The permissions for each view are checked in order. All matching roles are checked, until permission
is granted for that role.

As an example in *retrieve* an admin user matches both roles ('user' and 'admin'). However when
trying to retrieve another user's info, the first rule does not grant access so the checking will
continue. On the second rule, permission is granted and the checking ends there.


Advanced example
----------------

Sometimes you want to deal with more complex scenarios. Such refinement otherwise hairy
with `permission_classes`, becomes much simpler.

In the example below we have many more advanced scenarios including forbidding the user
to update their email.

views.py
```python
from rest_framework_roles.permissions import is_self
from rest_framework_roles import roles


def not_updating_email(request, view):
    return 'email' not in request.data


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
        'update': {
          'user': (is_self, not_updating_email),  # User can update everything but their email
          'admin': True,
        },
        'create': {'anon': True},W
        'list': {'admin': True},
        'me': {'user': True},
    }

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        if request.method == 'GET':
            return self.retrieve(request)
        elif request.method == 'PATCH':
            return self.partial_update(request)
```


Advanced roles
--------------

By default you get some role-checking functions for common roles like 'admin', 'user' and 'anon'.
Many times though, you'll have much more roles and certain roles can be expensive to calculate.

We can easily mark the role-checking functions with a cost. The lower cost roles are checked
first and then the expensive ones later. The cost is an arbitrary number so this refinement can
be as deep as you wish.


```python
from rest_framework_roles.decorators import role_checker


@role_checker(cost=0)
def is_freebie_user(request, view):
    return request.user.is_authenticated and request.user.plan == 'freebie'


@role_checker(cost=0)
def is_payed_user(request, view):
    return request.user.is_authenticated and not request.user.plan


@role_checker(cost=50)
def is_creator(request, view):
    obj = view.get_object()
    if hasattr(obj, 'creator'):
        return request.user == obj.creator
    return False
```

> This is a bit similar to Django REST's `check_permissions` and `check_object_permissions` which in this case
would translate to a max of 2 different costs.
