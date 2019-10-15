from pytest import fixture
from django.contrib.auth.models import User, AnonymousUser


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
