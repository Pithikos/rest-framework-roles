REST Framework Roles
====================

Role-based permissions that make sense.

  - Decouple permission logic from views and models.
  - Implementation agnostic. Permissions can utilize the database or be just a dict.
  - Support for Django and REST Framework. Class-based views or functions.
  - Support redirection without breaking permissions.


Install
-------


Install

    pip install rest_framework_roles


Usage
-----

Read on docs/usage.md


REST Framework integration
-------------------------------

You can mix roles and REST permissions but there is a caveat. You **cannot** use
`permission_classes` and `view_permissions` in the same class. This is because
`permission_classes` target permissions for the whole class while `view_permissions`
targets individual views.

This will not work and you'll get an error

    class MyViewSet():
        permission_classes = (IsAdminUser,)

        @allowed('admin')
        def myview1(self, request):
          pass

This is fine

    class MyViewSet():
        permission_classes = (IsAdminUser,)
        def myview(self, request):
          pass

    class MyOtherViewSet():
        @allowed('admin')
        def myview(self, request):
          pass

This also means that if no view permissions are defined, the defaults of REST Framework
will be used.


TODO
----

* Determine if we should move REST's check_permissions inside before_view
* Check is owner does not work for action 'me'
  - No pk passed
* Allow setting action permission for specific field on partial updates.
  e.g. {'partial_update:username': False}
* Allow checking action_map maybe
    In [9]: self.action_map                                                                                  
    Out[9]: {'get': 'me', 'patch': 'me'}
* Add checks to ensure pytest fixtures if they exist, validate against checkers. (to avoid bugs in tests)
