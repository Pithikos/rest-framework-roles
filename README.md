REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles) [![PyPI version](https://badge.fury.io/py/rest-framework-roles.svg)](https://badge.fury.io/py/rest-framework-roles)

A Django REST Framework security-centric plugin aimed at decoupling permissions from your models and views.

Features:

  - Least privilege by default.
  - Guard your API **before** a request reaches a view.
  - Redirections are guarded automatically.
  - Backwards compatible with DRF's `permission_classes`.

The framework provides `view_permissions` as an alternative to DRF's `permission_classes`, with the aim to move permission logic away from views and models so that views can focus on the business logic.


Installation
============

Install

    pip install rest-framework-roles

Edit your *settings.py* file

```python
INSTALLED_APPS = {
    ..
    'rest_framework',
    'rest_framework_roles',  # Must be after rest_framework
}

REST_FRAMEWORK_ROLES = {
  'ROLES': 'myproject.roles.ROLES',
  'DEFAULT_EXCEPTION_CLASS': 'rest_framework.exceptions.NotFound',
}
```

At this point all your views are protected and trying to access an endpoint will default to `DEFAULT_EXCEPTION_CLASS`.

Endpoints from *django.contrib* are not patched. If you wish to explicitly set what modules are patched you can edit the SKIP_MODULES setting like below.

```python
REST_FRAMEWORK_ROLES = {
  'ROLES': 'myproject.roles.ROLES',
  'SKIP_MODULES': [
    'django.*',
    'myproject.myapp55.*',
  ],
}
```


Specify roles
===========================

Create a file *roles.py* in your project to hold the defined roles in your application. Below we use the defactor Django roles and also add a few new ones for demonstration.


*roles.py*
```python
from rest_framework_roles.roles import is_anon, is_user, is_admin, is_staff

def is_buyer(request, view):
    return is_user(request, view) and request.user.usertype = 'buyer'

def is_seller(request, view):
    return is_user(request, view) and request.user.usertype = 'seller'


ROLES = {
    # Django vanilla roles
    'anon': is_anon,
    'user': is_user,
    'admin': is_admin,
    'staff': is_staff,

    # Some custom role examples
    'buyer': is_buyer,
    'seller': is_seller,
}
```

We call `is_buyer` and `is_seller` role checkers and their sole purpose is to determine if a request matches a specific role. They all take a `request` and `view` as parameters, similar to [DRF's behaviour](https://www.django-rest-framework.org/api-guide/permissions/). You can find the source for the provided shortcuts [here](https://github.com/Pithikos/rest-framework-roles/blob/master/rest_framework_roles/roles.py).


Specify view permissions
===========================

Once roles are defined, they can be used directly in `view_permissions`.

The example below demonstrates a typical behaviour one might want for a user management endpoint, mixing private and public actions. Furthermore it shows how we can return ad-hoc exceptions for certain actions.

*views.py*
```python
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework_roles.granting import is_self


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    view_permissions = {

        # Only anonymous requests can create users
        'create': {
            'anon': True,              #  OK for anonymous requests
            'user': PermissionDenied,  # 403 for logged-in users
        },

        # Only admins can list users
        'list': {
            'admin': True,             # admin can list all users
            'user': PermissionDenied,  # 403 for logged-in users who are not admins
            'anon': NotAuthenticated,  # 401 for anonymous requests
        },
        
        # Any user can retrieve themselves
        'retrieve,me': {
            'user': is_self,           # 404 fallback for anonymous requests
        },

        # Only admins can update users or users themselves
        'update,update_partial': {
            'user': is_self,           # OK for themselves
            'admin': True,             # OK for admins
        },
    }

    @action(detail=False, methods=['get'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        return self.retrieve(request)
```

> Redirections (e.g. `me`) are supported by the framework but you still need to explicitly state the views involved. Redirections have minimal performance impact.

> Note that the checking is **greedy**. If a request matches multiple roles, it will go through all of the roles until it reaches one that is granted access. This allows flexibility in case you have several overlapping roles (e.g. admin is also a user and staff).

> In a view you can always check `_view_permissions` to see what permissions are in effect.


Advanced setup
==============

Bypassing the framework
-----------------------
By default the framework patches DRF's `permission_classes` with `DefaultPermission` which simply raises the exception you defined in `DEFAULT_EXCEPTION_CLASS`. You can bypass this behaviour by simply setting `permission_classes` in your view class.

```python
class MyViewSet():
    permission_classes = [AllowAny]  # default DRF behaviour
```


Granting permission
-------------------

You can use the helper functions `allof` or `anyof` when deciding if a matched role should be granted access

```python
from rest_framework_roles.granting import allof

def not_updating_email(request, view):
    return 'email' not in request.data

class UserViewSet(ModelViewSet):
    view_permissions = {
        'update,partial_update': {
            'user': allof(is_self, not_updating_email),
            'admin': True,
        },
    }
```

In the above example the user can only update their information only while not trying to update their email.

> Ideally keep the grant checking functions in a file like *granting.py* or above your viewsets. Keep in mind; (1) a request can get matched to a role (2) but granting determines if the role will be granted access.


Optimizing role checking
------------------------

You can change the order of how roles are checked. This makes sense if you want
less frequent or expensive checks to happen prior to infrequent and slower ones.


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

In this example, roles with cost 0 would be checked first, and lastly the *creator* role would be checked since it has the highest cost.

> Note this is similar to Django REST's `check_permissions` and `check_object_permissions` but more generic & flexible since it allows an arbitrary number of costs.
