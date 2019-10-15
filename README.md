REST Framework Roles
====================

Data-driven no-database permissions based on simple roles. The check occurs as
middleware, decoupling permission and roles totally from your views.


Install
-------


Install

    pip install rest_framework_roles


Usage
-----

Read on docs/usage.md



TODO
----

* Check is owner does not work for action 'me'
  - No pk passed
* Allow setting action permission for specific field on partial updates.
  e.g. {'partial_update:username': False}
* Allow checking action_map maybe
    In [9]: self.action_map                                                                                  
    Out[9]: {'get': 'me', 'patch': 'me'}
* Add checks to ensure pytest fixtures if they exist, validate against checkers. (to avoid bugs in tests)
