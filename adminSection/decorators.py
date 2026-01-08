from django.shortcuts import redirect
from django.contrib import messages

def coordinator_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to access this page.')
            return redirect('login')
        if request.user.profile.user_type != 'coordinator':
            messages.error(request, 'Only coordinators can access this page.')
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper