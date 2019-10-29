import django
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.urls import path, include
from django.http import HttpResponse
from rest_framework import routers, permissions, viewsets, views, decorators, generics
import rest_framework as drf


from ..utils import UserSerializer, _func_name


def django_function_view(request):
    return HttpResponse(_func_name())


@drf.decorators.api_view()
def rest_function_view(request):
    # This behaves exactly the same as if it was a method of APIView
    return HttpResponse(_func_name())


class DjangoView(django.views.generic.ListView):
    model = User

    def get(self, request):
        return HttpResponse(_func_name())

    def not_a_view(self, *args, **kwargs):
        # Not a view since not the standard get, post, etc.
        return HttpResponse(_func_name())


class RestAPIView(drf.views.APIView):  # This is the mother class of all classes
    serializer_class = UserSerializer
    permission_classes = (drf.permissions.AllowAny,)
    queryset = User.objects.all()

    def get(self, request):
        return HttpResponse(_func_name())

    def not_a_view(self, *args, **kwargs):
        # Not a view since not marked with decorator
        return HttpResponse(_func_name())


class RestViewSet(drf.viewsets.ViewSet):
    def list(self, request):
        return HttpResponse(_func_name())

    def custom_view(self, request):
        return HttpResponse(_func_name())

    # TODO: This is not tested atm
    @drf.decorators.action(detail=False, methods=['get'], url_name='custom_action', url_path='custom_action')
    def custom_action(self, request):
        return HttpResponse(_func_name())


urlpatterns = []
function_based_patterns = {
    '/django_function_view': path('django_function_view', django_function_view),
}
class_based_patterns = {
    '/rest_function_view': path('rest_function_view', rest_function_view),  # internally ends up being a method
    '/django_class_view': path('django_class_view', DjangoView.as_view()),
    '/rest_class_view': path('rest_class_view', RestAPIView.as_view()),
}
viewset_based_patterns = {
    '/rest_class_viewset': path('rest_class_viewset', RestViewSet.as_view({'get': 'list'})),
    '/rest_class_viewset/custom_view': path('rest_class_viewset/custom_view', RestViewSet.as_view({'get': 'custom_view'})),
    # NOTE: `custom_action` path is autopopulated by REST Framework
}
