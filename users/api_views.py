from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.middleware.csrf import get_token
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.contrib.sessions.models import Session
from django.contrib.auth import update_session_auth_hash
from .decorators import api_login_required, api_admin_required
from .models import UserSession
import json
import logging
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)

User = get_user_model()

@api_login_required
@require_http_methods(["GET"])
def api_users_list(request):
    """
    Enterprise Users API - List users with pagination and search
    """
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        search = request.GET.get('search', '').strip()
        per_page = int(request.GET.get('per_page', 10))
        
        # Build queryset
        queryset = User.objects.all().order_by('username')
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Paginate results
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        # Serialize users
        users_data = []
        for user in page_obj:
            # Determine user role
            if user.is_superuser:
                role = 'Admin'
            elif user.is_staff:
                role = 'Manager'
            else:
                role = 'User'
            
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.username,
                'role': role,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            })
        
        return JsonResponse({
            'success': True,
            'data': users_data,
            'users': users_data,  # Backward compatibility
            'pagination': {
                'page': page_obj.number,
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'pages': paginator.num_pages,
                'total_count': paginator.count,
                'count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'per_page': per_page
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_user_update_role(request):
    """
    Enterprise Role Update API - Simplified and Robust
    """
    # Validate authentication
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    # Validate permissions
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Staff privileges required'}, status=403)
    
    try:
        # Log request details for debugging
        logger.info(f'Role update request: {request.method} {request.get_full_path()}')
        logger.info(f'Content-Type: {request.content_type}')
        logger.info(f'Request body: {request.body.decode("utf-8") if request.body else "Empty"}')
        logger.info(f'Request POST: {dict(request.POST)}')
        
        # Handle multiple request formats
        if request.content_type == 'application/json':
            data = json.loads(request.body) if request.body else {}
        else:
            data = request.POST.dict()
        
        logger.info(f'Parsed data: {data}')
        
        # Extract data with multiple field name support
        user_id = data.get('user_id') or data.get('userId') or data.get('id')
        new_role = (data.get('role') or data.get('newRole') or '').strip()
        
        # Validate input with debug info
        if not user_id:
            return JsonResponse({
                'success': False, 
                'error': 'User ID required',
                'received_data': data,
                'content_type': request.content_type
            }, status=400)
        
        # Normalize role input (handle both display and database values)
        role_normalization = {
            'Admin': 'Admin', 'admin': 'Admin', 'ADMIN': 'Admin',
            'Manager': 'Manager', 'manager': 'Manager', 'MANAGER': 'Manager',
            'User': 'User', 'user': 'User', 'USER': 'User'
        }
        
        normalized_role = role_normalization.get(new_role)
        if not normalized_role:
            return JsonResponse({
                'success': False, 
                'error': 'Valid role required (Admin/Manager/User)',
                'received_role': new_role,
                'valid_roles': list(role_normalization.keys()),
                'received_data': data
            }, status=400)
        
        new_role = normalized_role
        
        # Get target user
        try:
            target_user = User.objects.get(id=int(user_id))
        except (ValueError, User.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Security checks
        if target_user == request.user and new_role != 'Admin' and request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Cannot demote yourself'}, status=400)
        if new_role == 'Admin' and not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Only admins can create admins'}, status=403)
        
        # Map role to permissions using model constants
        role_mapping = {
            'Admin': {'is_staff': True, 'is_superuser': True, 'role': User.ADMIN},
            'Manager': {'is_staff': True, 'is_superuser': False, 'role': User.MANAGER},
            'User': {'is_staff': False, 'is_superuser': False, 'role': User.USER}
        }
        
        permissions = role_mapping[new_role]
        
        # Update user atomically
        with transaction.atomic():
            target_user.is_staff = permissions['is_staff']
            target_user.is_superuser = permissions['is_superuser']
            target_user.role = permissions['role']
            target_user.save(update_fields=['is_staff', 'is_superuser', 'role'])
        
        return JsonResponse({
            'success': True,
            'message': f'User {target_user.username} updated to {new_role}',
            'user': {
                'id': target_user.id,
                'username': target_user.username,
                'role': new_role,
                'is_staff': target_user.is_staff,
                'is_superuser': target_user.is_superuser
            }
        })
        
    except json.JSONDecodeError as e:
        logger.error(f'JSON decode error: {e}')
        return JsonResponse({
            'success': False, 
            'error': 'Invalid JSON format',
            'details': str(e),
            'request_body': request.body.decode('utf-8') if request.body else None
        }, status=400)
    except Exception as e:
        logger.error(f'Role update error: {e}', exc_info=True)
        return JsonResponse({
            'success': False, 
            'error': 'Update failed',
            'details': str(e)
        }, status=500)
        
    except json.JSONDecodeError as e:
        logger.error(f'JSON decode error in user role update: {e}')
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data',
            'details': str(e)
        }, status=400)
    except ValueError as e:
        logger.error(f'Value error in user role update: {e}')
        return JsonResponse({
            'success': False,
            'error': 'Invalid data format',
            'details': str(e)
        }, status=400)
    except User.DoesNotExist as e:
        logger.error(f'User not found in role update: {e}')
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        logger.error(f'Unexpected error in user role update: {e}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_user_create(request):
    """
    Enterprise Users API - Create a new user and assign role
    Admin-only. Accepts form-encoded or JSON.
    Fields: username, email, first_name, last_name, role (Admin/Manager/User), password (optional)
    """
    # Authn
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    # Authz: only superuser can create users with Admin role; staff can create up to Manager
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Staff privileges required'}, status=403)

    try:
        # Parse payload
        if request.content_type == 'application/json':
            data = json.loads(request.body or '{}')
        else:
            data = request.POST.dict()

        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        role_input = (data.get('role') or '').strip()
        password = data.get('password')  # may be None/empty

        if not username or not email:
            return JsonResponse({'success': False, 'error': 'username and email are required'}, status=400)

        # Normalize role
        role_normalization = {
            'Admin': 'Admin', 'admin': 'Admin', 'ADMIN': 'Admin',
            'Manager': 'Manager', 'manager': 'Manager', 'MANAGER': 'Manager',
            'User': 'User', 'user': 'User', 'USER': 'User'
        }
        normalized_role = role_normalization.get(role_input) or 'User'

        # Enforce privileges
        if normalized_role == 'Admin' and not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Only admins can create admins'}, status=403)

        role_mapping = {
            'Admin': {'is_staff': True, 'is_superuser': True, 'role': User.ADMIN},
            'Manager': {'is_staff': True, 'is_superuser': False, 'role': User.MANAGER},
            'User': {'is_staff': False, 'is_superuser': False, 'role': User.USER}
        }
        perms = role_mapping[normalized_role]

        if not password:
            password = get_random_string(12)
            generated_password = True
        else:
            generated_password = False

        # Create user atomically
        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Username already exists'}, status=400)
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)

            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=perms['is_staff'],
                is_superuser=perms['is_superuser'],
                role=perms['role'],
                is_active=True,
            )
            user.set_password(password)
            # invitation flags for enterprise onboarding
            user.force_password_change = True if generated_password else False
            user.generate_invitation_token()
            user.save()

        return JsonResponse({
            'success': True,
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': normalized_role,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            },
            'temporary_password': password if generated_password else None,
            'invitation_token': user.invitation_token,
        })
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': 'Invalid JSON', 'details': str(e)}, status=400)
    except Exception as e:
        logger.error(f'User create error: {e}', exc_info=True)
        return JsonResponse({'success': False, 'error': 'Creation failed', 'details': str(e)}, status=500)

@api_login_required
@require_http_methods(["GET"])
def api_csrf_token(request):
    """
    Enterprise API - Get CSRF token for authenticated requests
    """
    try:
        return JsonResponse({
            'success': True,
            'csrf_token': get_token(request)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_test_role_update(request):
    """
    Test endpoint for role update debugging
    """
    try:
        data = json.loads(request.body) if request.body else {}
        test_role = data.get('role', '')
        
        # Test role normalization
        role_normalization = {
            'Admin': 'Admin', 'admin': 'Admin', 'ADMIN': 'Admin',
            'Manager': 'Manager', 'manager': 'Manager', 'MANAGER': 'Manager',
            'User': 'User', 'user': 'User', 'USER': 'User'
        }
        
        normalized_role = role_normalization.get(test_role)
        
        return JsonResponse({
            'success': True,
            'message': 'Test endpoint working',
            'role_test': {
                'received_role': test_role,
                'normalized_role': normalized_role,
                'is_valid': normalized_role is not None,
                'valid_roles': list(role_normalization.keys())
            },
            'request_data': {
                'method': request.method,
                'content_type': request.content_type,
                'body': request.body.decode('utf-8') if request.body else None,
                'parsed_data': data,
                'user': request.user.username if request.user.is_authenticated else 'Anonymous',
                'is_staff': request.user.is_staff if request.user.is_authenticated else False,
                'is_superuser': request.user.is_superuser if request.user.is_authenticated else False
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'request_body': request.body.decode('utf-8') if request.body else None
        })

@api_login_required
@require_http_methods(["GET"])
def api_user_details(request, user_id):
    """
    Enterprise API - Get specific user details for verification
    """
    try:
        user_id = int(user_id)
        user = User.objects.get(id=user_id)
        
        # Determine user role
        if user.is_superuser:
            role = 'Admin'
        elif user.is_staff:
            role = 'Manager'
        else:
            role = 'User'
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'role': role,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active
            }
        })
        
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'error': 'Invalid user ID format'
        }, status=400)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_login_required
@require_http_methods(["GET"])
def api_current_user_permissions(request):
    """
    Enterprise Users API - Get current user permissions
    """
    try:
        user = request.user
        
        # Determine user role
        if user.is_superuser:
            role = 'Admin'
        elif user.is_staff:
            role = 'Manager'
        else:
            role = 'User'
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'role': role,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'permissions': {
                    'can_manage_users': user.is_superuser,
                    'can_view_audit': user.is_staff,
                    'can_manage_assets': user.is_staff,
                    'can_generate_reports': user.is_staff
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)