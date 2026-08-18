from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods


@login_required
@user_passes_test(lambda user: user.role == 'admin' or user.is_superuser)
@require_http_methods(["GET"])
def category_list(request):
    """Category management page - displays all asset categories."""
    return render(request, 'categories/category_list.html')
