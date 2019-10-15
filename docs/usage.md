Usage
=====


Basic configuration
-------------------

settings.py
```python

INSTALLED_APPDS = {
    ..
    'rest_framework',
    'rest_framework_roles',  # Must be after rest_framework
}

REST_FRAMEWORK_ROLES = {
  'roles': 'fileshare.roles.ROLES',
  'role_permissions': 'fileshare.permissions.VIEW_PERMISSIONS',
}
```

roles.py
```python
from rest_framework_roles import is_user, is_anon

ROLES = {
  'anonymous': {'role_checker': is_anon},
  'user': {'role_checker': is_user},
}
```

permissions.py
```python
VIEW_PERMISSIONS = [
    {
        'model': 'fileshare.models.User',
        'permissions': {
            'owner': {
                '__all__': True,
            },
            'anon': {
                'create': True,
            },
            'user': {
                'list': True,
                'retrieve': True,
            }
        }
    }
]
```

Writing role checkers
---------------------

A checker is a function that will be always passed a view and a request and needs
to return a boolean.

For example to see if someone is the owner one would do the below for Django REST Framework

roles.py
```
def is_creator(view, request):
    obj = view.get_object()
    return request.user == obj.creator

ROLES = {
    'owner': is_creator,
}
```

Checkers can also be used when setting role permissions like below

permissions.py
```
def is_updating_serial_number(view, request):
    return 'serial_number' in request.data

PERMISSIONS = {
    'view': 'myapp.views.ProductViewSet',
    'permissions': {
      'owner': {
          'create': True,
          'destroy': True,
          'update': not is_updating_serial_number,
      }
    }
}
```
