REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles)


Role-based permissions for Django and Django REST Framework (functions or classes).

  - Decouple permissions from views and models.
  - Easy declarative configuration (still allowing complex scenarios).
  - View redirection works out-of-the-box.
  - Gradual integration with existing projects.


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


Usage
-----


First you need to define some roles. Below we use the ones already working with Django out-of-the-box.

roles.py
```python
from rest_framework_roles.roles import is_user, is_anon, is_admin


ROLES = {
    'admin': is_admin,
    'user': is_user,
    'anon': is_anon,
}
```

`is_admin`, `is_user` and `is_anon` are simple functions that take `request` and `view` as arguments and return a boolean - denoting if a user request matches a role.

We now need to define when permission should be granted for a matching role.

views.py
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework_roles.granting import is_self

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

In this example only anonymous users can create a new user account. Admin can retrieve any user's acount and list users. Users can only retrieve their own information.

 You can use any of **@allowed**, **@disallowed** or **view_permissions** to specify permissions.



How it works
------------

The library is using a permission table internally but at a high level the behaviour is outlined below

1. First roles are checked in order of cost (as set by `@role_checker`)
2. A matching role is further checked to see if permission is granted.
  - Truthful booleans and functions will grant permission.
  - In case of a collection (e.g. `@anyof`), the grant checkers are evaluated in order. If truthful, permission is granted.
  - In case of not a truthful result, we fallback to the framework permissions. For REST Framework
     that is `permission_classes`.


Note in the snippet below, admin is a user so he would match both roles. However the first rule will
not grant permission, while the second will.

    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
    }

For more **complex scenarios** you can specify multiple functions to be checked when determining if permission should be granted.

    from rest_framework_roles.granting import allof

    def not_updating_email(request, view):
        return 'email' not in request.data

    class UserViewSet(ModelViewSet):
        view_permissions = {
            'update': {
              'user': allof(is_self, not_updating_email),
              'admin': True,
            },
        }
    ..

In this case the user can only update their information as long as they don't update their email.



Role checking order
-------------------

Roles are checked in order of cost.


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

In this example, roles with cost 0 would be checked first, and lastly the *creator* role would be checked.

> Note this is similar to Django REST's `check_permissions` and `check_object_permissions` but with much more room for refinement since you can have arbitrary number of costs.
