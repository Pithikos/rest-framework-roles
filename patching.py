import sys
from .views import PatchedAPIView

# We replace the Django REST view with our patched one
sys.modules['rest_framework'].views.APIView = PatchedAPIView
