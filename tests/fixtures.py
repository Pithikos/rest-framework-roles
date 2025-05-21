from pytest import fixture
from django.test import RequestFactory
from django.contrib.auth.models import User, AnonymousUser


@fixture
def client():
    from rest_framework.test import APIClient
    return APIClient()

@fixture
def anon(db):
    return AnonymousUser()

@fixture
def user(db):
    return User.objects.create(
        username='mruser',
    )

@fixture
def admin(db):
    return User.objects.create(
        username='mradmin',
        is_staff=True,
        is_superuser=True,
    )
    
@fixture
def test_user1(db):
    return User.objects.create(
        username='test_user1',
    )

@fixture
def test_user2(db):
    return User.objects.create(
        username='test_user2',
    )

@fixture
def test_user3(db):
    return User.objects.create(
        username='test_user3',
    )

@fixture(scope='function')
def request_factory():
    return RequestFactory()
