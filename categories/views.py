from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


@login_required
@require_http_methods(["GET"])
def category_list(request):
    """Category management page - displays all asset categories."""
    return render(request, 'categories/category_list.html')
