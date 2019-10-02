from django.conf import settings
from rest_framework.views import APIView as OriginalAPIView

from .parsing import create_lookup


VIEW_PERMISSIONS = create_lookup()


def view_path(view):
    return view.__module__ + '.' + view.__class__.__name__


def view_method_wrapper(view, func):
    """ Wraps every specified method """
    def wrapped(request, *args, **kwargs):
        action = func.__name__
        checkers = VIEW_PERMISSIONS[view_path(view)][action]

        for checker in checkers['role_checkers']:
            if not checker().has_role(request):
                view.permission_denied(request, message='Permission denied')

        if checkers['role_object_checkers']:
            # obj = view.get_object()
            # import IPython; IPython.embed(using=False)
            for checker in role_object_checkers:
                if not checker().has_object_role(request, obj):
                    view.permission_denied(request, message='Permission denied')

        print(f"Wrapper: {view} {action}")
        import IPython; IPython.embed(using=False)
        return func(request, *args, **kwargs)
    return wrapped


class PatchedAPIView(OriginalAPIView):
    """ Patches permission checking functions so that we can check by role """

    def __init__(self, *args, **kwargs):
        parent = super(OriginalAPIView, self)
        parent.__init__(*args, **kwargs)

        try:
            actions_lookup = VIEW_PERMISSIONS[view_path(self)]
        except KeyError:
            return None

        # Monkey-patch child's methods
        for action, checkers in actions_lookup.items():
            if not hasattr(self, action):
                continue

            # Decorate existing view method
            original_func = getattr(self, action)
            setattr(self, action, view_method_wrapper(self, original_func))

            # import IPython; IPython.embed(using=False)
            # for attr, val in self.__dict__.iteritems():
            #     if callable(val) and not attr.startswith("__"):
            #         setattr(self, attr, smileDeco(val))
            # setattr(self, action, action_wrapper)


            # original_func_name = f'_original_{action}'
            # setattr(self, original_func_name, original_func)
            # gl = globals()
            # import IPython; IPython.embed(using=False)
            #
            # def action_wrapper(func):
            #     import IPython; IPython.embed(using=False)
            #     def function_wrapper(*args, **kwargs):
            #         print("Before calling " + func.__name__)
            #         return func(*args, **kwargs)
            #     return function_wrapper

            # def decorator(request)
            # def wrapper(request, *args, **kwargs):
            #     print(func.__name__)
            #     return
                # self = self  # ensures
                # orig = original_func
                # print('Calling function', self, args, kwargs)
                # import IPython; IPython.embed(using=False)
                # return setattr(self, f'_original_{action}', original_func)
                # return orig(*args, **kwargs)
            # setattr(self, action, action_wrapper)

    def get_checkers(self):
        try:
            checkers_by_action = VIEW_PERMISSIONS[view_path(self)]['role_checkers']
            return checkers_by_action.get(self.action) or \
                   checkers_by_action.get('*') or \
                   []
        except KeyError:
            return []

    def get_object_checkers(self):
        try:
            checkers_by_action = VIEW_PERMISSIONS[view_path(self)]['role_object_checkers']
            return checkers_by_action.get(self.action) or \
                   checkers_by_action.get('*') or \
                   []
        except KeyError:
            return []

    # def before_view(self):
    #     import IPython; IPython.embed(using=False)


    # def check_permissions(self, request):
    #     """ Called every time """
    #     # import IPython; IPython.embed(using=False)
    #     checkers = self.get_checkers()
    #     if not checkers:
    #         return OriginalAPIView.check_permissions(self, request)
    #
    #     # At this point we have checkers that need to match
    #     # import IPython; IPython.embed(using=False)
    #     for checker in checkers:
    #         if checker(request):
    #             return
    #     self.permission_denied(request, message='Permission denied')

    # def check_object_permissions(self, request, obj):
    #     """ Called by get_object() """
    #     checkers = self.get_object_checkers()
    #     if not checkers:
    #         return OriginalAPIView.check_object_permissions(self, request, obj)
    #
    #     # At this point we have checkers that need to match
    #     for checker in checkers:
    #         if checker(request):
    #             return
    #     self.permission_denied(request, message='Permission denied')


# Patch all views

# PatchedAPIView.VIEW_PERMISSIONS
# import IPython; IPython.embed(using=False)
