def is_self(view, request):
    return request.user == view.get_object()
