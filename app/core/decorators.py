# core/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def superuser_required(view_func):
    """Only Superuser can access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'superuser':
            raise PermissionDenied("Only Superuser can perform this action.")
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_or_superuser_required(view_func):
    """Manager and Superuser can access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['superuser', 'manager']:
            raise PermissionDenied("You don't have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return wrapper