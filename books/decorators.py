from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_required_custom(view_func):
    """Redirect to login if not authenticated."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this page.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Allow access only for Admin or SuperAdmin group members."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this page.")
            return redirect('login')
        if request.user.groups.filter(name__in=['Admin', 'SuperAdmin']).exists() or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('book_list')
    return wrapper


def superadmin_required(view_func):
    """Allow access only for SuperAdmin group members."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this page.")
            return redirect('login')
        if request.user.groups.filter(name='SuperAdmin').exists() or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, "Only Super Admins can perform this action.")
        return redirect('book_list')
    return wrapper
