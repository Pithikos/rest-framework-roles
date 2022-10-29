REST Framework Roles
====================

[![rest-framework-roles](https://circleci.com/gh/Pithikos/rest-framework-roles.svg?style=svg)](https://circleci.com/gh/Pithikos/rest-framework-roles) [![PyPI version](https://badge.fury.io/py/rest-framework-roles.svg)](https://badge.fury.io/py/rest-framework-roles)

Role-based permissions for Django REST Framework.

  - Least privileges by default.
  - Human readable **declarative** view-based permissions.
  - Switch between DRF's permission_classes and this easily.
  - Protects you from accidentally exposing an endpoint on **view redirections**.
  - Generic & flexible. You decide the where and how of your access logic and storage.

This works as a replacement for `permission_classes` on individual classes. This makes it easy to switch between this and the normal DRF behaviour depending on your needs.

Note that also `DEFAULT_PERMISSIONS_CLASSES` is patched so by default all endpoints will be denied access by simply installing this.


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

Now all your endpoints default to *403 Forbidden* unless you specifically use `view_permissions` or DRF's `permission_classes` in view classes.

By default endpoints from *django.contrib* won't be patched. If you wish to explicitly set what modules are skipped you can edit the SKIP_MODULES setting like below.

```python
REST_FRAMEWORK_ROLES = {
  'ROLES': 'myproject.roles.ROLES',
  'SKIP_MODULES': [
    'django.*',
    'myproject.myapp55.*',
  ],
}
```


Setting permissions
===================


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

    # Some custom role examples
    'buyer': is_buyer,
    'seller': is_seller,
}
```

`is_admin`, `is_user`, etc. are simple functions that take `request` and `view` as parameters, similar to [DRF's behaviour](https://www.django-rest-framework.org/api-guide/permissions/).


Next we need to define permissions for the views with `view_permissions`.

*views.py*
```python
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework_roles.granting import is_self


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    # you can define permissions at the view level
    view_permissions = {
        'create': {'anon': True},  # only anonymous visitors allowed
        'list': {'admin': True}, 
        'retrieve,me': {'user': is_self},
        'update,update_partial': {'user': is_self, 'admin': True},
    }

    @action(detail=False, methods=['get'])
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        return self.retrieve(request)
```

By default everyone is denied access to everything. So we need to 'whitelist' any views
we want to give permission explicitly.

For redirections like `me` (which redirects to `retrieve`), we need to give the same permissions to both or else we'll get 403 Forbidden.

> In a view you can always check `_view_permissions` to see what permissions are in effect.

> A request keeps track of all permissions checked so far. So  redirections don't affect performance since the same permissions are never checked twice.


Advanced setup
==============

Bypassing the framework
-----------------------
If you want to bypass the framework in a specific view class just explicitly set the `permission_classes`.

```python
class MyViewSet():
    permission_classes = [AllowAny]
```

By default when you install DRF, every class gets automatically populated `permission_classes = [AllowAny]` which is really a bad idea. If for some reason you wish to get the same behaviour, you'd need to add `permission_classes = [AllowAny]` on every individual class.


Granting permission
-------------------

You can use the helper functions `allof` or `anyof` when deciding if a matched role should
be granted access

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

> You can put all these functions inside a new file *granting.py* or just keep them close to the views, depending on what makes sense for your case. It's **important to not mix them with the roles** though to keeps things clean; (1) a role identifies someone making the request while (2) granting determines if the person fitting tha role should be granted permission for their request. 

> Keep in mind that someone can fit multiple roles. E.g. `admin` is also a user (unless you change the implementation of `is_user` and `is_admin`).


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

> Note this is similar to Django REST's `check_permissions` and `check_object_permissions` but more generic & adjustable since you can have arbitrary number of costs (instead of 2).
