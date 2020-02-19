from django.apps import AppConfig


class RestFrameworkRolesConfig(AppConfig):
    name = 'rest_framework_roles'
    verbose_name = 'REST Framework Roles'

    def ready(self):
        from .patching import patch
        patch()
