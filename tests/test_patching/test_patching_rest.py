import importlib
from unittest.mock import patch, MagicMock, Mock, call

import pytest
from django.urls import get_resolver
from rest_framework.test import APIRequestFactory

from ..fixtures import admin, user, anon
import patching
from patching import is_method_view, get_view_class
from .urls import *


@pytest.mark.urls(__name__)
class TestPatchClassViews():
    """
    REST functions behave excactly the same as methods. They become methods
    of the class WrappedAPI.
    """

    def setup(self):
        global urlpatterns
        urlpatterns = class_based_patterns.values()
        patching.patch()  # Ensure patching occurs!
        self.urlconf = importlib.import_module(__name__)
        self.resolver = get_resolver(self.urlconf)

    def test_dispatch_is_not_patched(self):
        match = self.resolver.resolve('/rest_function_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'
        match = self.resolver.resolve('/rest_class_view')
        assert match.func.__wrapped__.__wrapped__.__name__ == 'dispatch'

    def test_method_views_patching(self, client, admin):
        """
        We expect the below order:

            dispatch -> get -> view wrapper -> view method
        """
        for url, view_name in (
                ('/rest_function_view', 'rest_function_view'),
                ('/rest_class_view', 'get'),
            ):

            match = self.resolver.resolve(url)
            request = APIRequestFactory().get(url)
            cls = match.func.view_class
            inst = cls()
            # import IPython; IPython.embed(using=False)

            calls = []
            def mark_called_dispatch(*args):
                calls.append('dispatch')
            def mark_called_view_wrapper(*args):
                calls.append('view_wrapper')

            # Keep track of order the functions are called
            with patch.object(cls, 'dispatch', wraps=inst.dispatch) as mock_dispatch:
                mock_dispatch.side_effect = mark_called_dispatch
                with patch('patching.before_view') as mock_before_view:
                    mock_before_view.side_effect = mark_called_view_wrapper
                    # TODO: Test view was called after the view_wrapper
                    response = match.func(request)
                    assert response.status_code == 200
                    assert response.content.decode() == view_name
                    assert calls == ['dispatch', 'view_wrapper']
