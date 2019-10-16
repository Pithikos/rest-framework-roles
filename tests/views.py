from rest_framework import serializers
from rest_framework import permissions
from rest_framework import viewsets

from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)
    queryset = User.objects.all()
    view_permissions = {}
