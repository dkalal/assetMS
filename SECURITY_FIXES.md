# Critical Security Fixes for Production

## 1. Fix Path Traversal in assets/views.py (Line 669, 55)

Replace:
```python
file_path = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
```

With:
```python
from django.utils._os import safe_join
file_path = safe_join(settings.MEDIA_ROOT, 'reports', filename)
```

## 2. Add Missing Authorization Decorators

In `settings/views.py`, add to functions at lines 602 and 1115:
```python
from django.contrib.auth.decorators import login_required

@login_required
def your_view_function(request):
    # existing code
```

## 3. Fix Database Query Optimization

In `assets/views.py` line 1139, replace:
```python
AuditLog.objects.filter(action='scan').order_by('-timestamp')
```

With:
```python
AuditLog.objects.filter(action='scan').select_related('asset', 'user').order_by('-timestamp')
```

## 4. Sanitize JavaScript DOM Manipulation

In `static/js/` files, replace `innerHTML` with `textContent` for user data:
```javascript
// Instead of:
element.innerHTML = userData;

// Use:
element.textContent = userData;
```

These fixes will address the critical security vulnerabilities found in the code review.