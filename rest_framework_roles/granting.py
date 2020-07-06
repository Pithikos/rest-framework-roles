def is_self(request, view):
    return request.user == view.get_object()
