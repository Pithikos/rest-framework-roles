REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles) [![PyPI version](https://badge.fury.io/py/rest-framework-roles.svg)](https://badge.fury.io/py/rest-framework-roles)

Role-based permissions for Django REST Framework.

  - **Least privileges** by default.
  - Human readable **declarative** view-based permissions.
  - Protects you from accidentally exposing an endpoint on **view redirections**.
  - Generic & flexible. You decide the where and how of your access logic and storage.

There's a [ton of similar frameworks](https://www.django-rest-framework.org/api-guide/permissions/#third-party-packages) out there requiring you an IQ of 141 or a PhD to comprehend. Hopefully this will keep you productive and safe.


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
}
```


Configuration
=============


First you need to define some roles like below

*roles.py*
```python
from rest_framework_roles.roles import is_user, is_anon, is_admin


def is_buyer(request, view):
    return is_user(request, view) and request.user.usertype = 'buyer'

def is_seller(request, view):
    return is_user(request, view) and request.user.usertype = 'seller'


ROLES = {
    # Django out-of-the-box
    'admin': is_admin,
    'user': is_user,
    'anon': is_anon,

    # A few custom roles
    'buyer': is_buyer,
    'seller': is_seller,
}
```

`is_admin`, `is_user`, etc. are simple functions that take `request` and `view` as parameters just like [DRF's behaviour](https://www.django-rest-framework.org/api-guide/permissions/).


Next we need to define permissions for the views with `view_permissions`.

*views.py*
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework_roles.granting import is_self


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    view_permissions = {
        'retrieve': {'user': is_self, 'admin': True},
        'create': {'anon': True},
        'list': {'admin': True},
    }

    @action(detail=False, methods=['get'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        return self.retrieve(request)
```

Note that action `me` is just a redirect to the view `retrieve` so the permissions of *retrieve* will be used. You can specify a different permission for `me` as well, in which case both views will be checked.


Advanced usage
==============

Bypassing the framework
-----------------------
If you want to bypass the framework in a specific view class just explicitly set the `permission_classes` since we add our own `RolePermission` normally.

```python
class MyViewSet():
    permission_classes = [AllowAny]
```

Even if you bypass the framework that way, you can still protect individual views

```python
class MyViewSet():
    permission_classes = [AllowAny]
    view_permissions = {"list": {"admin": True}}
```

In this case `AllowAny` will be used for all views of the class, except `list` which will only allow admins.

> You can always check `_view_permissions` on a class view instance to determine what permissions are in effect.


Complex permission granting
---------------------------

For more complex scenarios where you want to determine if a role should be granted access or not to the endpoint, you can use the helper functions `allof` or `anyof`.

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

In this case the user can only update their information as long as they don't update their email.

> You can put all these functions inside a new file *granting.py* or just keep them close to the views, depending on what makes sense for your case. It's **important to not mix them with the roles** though to keeps things clean; a role identifies someone making the request. Granting determines if the person fitting tha role should be granted permission for their request. 

> Also keep in mind that someone can fit multiple roles. E.g. `admin` is also a user (unless you change the implementation of `is_user` and `is_admin`).


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

> Note this is similar to Django REST's `check_permissions` and `check_object_permissions` but with much more room for refinement since you can have arbitrary number of costs.
