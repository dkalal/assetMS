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
from .models import UserSession, RolePermissionMatrix
from . import utils as user_utils
from audit.models import AuditEvent
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
        
        # Resolve company context
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)

        # Build queryset scoped to company with branch relationship
        queryset = User.objects.select_related('company').prefetch_related(
            'user_branches__branch'
        ).filter(company=company).order_by('username')
        
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
            
            # Get primary branch information
            branch_id = None
            branch_name = None
            primary_branch_rel = user.user_branches.filter(is_primary=True).first()
            if primary_branch_rel and primary_branch_rel.branch:
                branch_id = primary_branch_rel.branch.id
                branch_name = primary_branch_rel.branch.name
            
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
                'branch_id': branch_id,
                'branch_name': branch_name,
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

@api_login_required
@require_http_methods(["GET", "POST"])
def api_roles_permissions(request):
    """Admin-only API to view/update Role Permission Matrix.
    GET -> returns current matrix
    POST -> updates matrix (CSRF required)
    """
    try:
        # Admin-only access: allow global superuser or system_admin user.
        # This keeps RolePermissionMatrix changes restricted to system-level
        # operators, separate from per-company admins/managers.
        if not (request.user.is_superuser or getattr(request.user, 'is_system_admin', False)):
            return JsonResponse({'success': False, 'error': 'Admin privileges required'}, status=403)

        if request.method == 'GET':
            matrix = RolePermissionMatrix.load()
            return JsonResponse({'success': True, 'matrix': matrix.permissions, 'updated_at': matrix.updated_at.isoformat()})

        # POST: validate CSRF via default middleware (no csrf_exempt here)
        if request.content_type == 'application/json':
            data = json.loads(request.body or '{}')
        else:
            data = request.POST.dict()

        proposed = data.get('matrix') or data.get('permissions') or {}

        # Validate structure: {role: [permission_code, ...]}
        if not isinstance(proposed, dict):
            return JsonResponse({'success': False, 'error': 'matrix must be a JSON object'}, status=400)

        allowed_roles = {'Admin', 'Manager', 'User'}
        normalized = {}
        for role, perms in proposed.items():
            if role not in allowed_roles:
                return JsonResponse({'success': False, 'error': f'Unknown role: {role}'}, status=400)
            if not isinstance(perms, (list, tuple)):
                return JsonResponse({'success': False, 'error': f'Permissions for {role} must be a list'}, status=400)
            # Deduplicate and normalize to strings
            cleaned = []
            seen = set()
            for p in perms:
                if not isinstance(p, str):
                    return JsonResponse({'success': False, 'error': f'Permission codes must be strings (role {role})'}, status=400)
                code = p.strip()
                if not code:
                    continue
                if code not in seen:
                    seen.add(code)
                    cleaned.append(code)
            normalized[role] = cleaned

        # Always preserve keys for all roles
        for r in allowed_roles:
            normalized.setdefault(r, [])

        with transaction.atomic():
            matrix = RolePermissionMatrix.load()
            matrix.permissions = normalized
            matrix.save(update_fields=['permissions', 'updated_at'])
            # Invalidate cache so subsequent checks reflect new values
            try:
                user_utils.invalidate_permissions_cache()
            except Exception:
                pass

        logger.info('Role Permission Matrix updated by %s', request.user.username)
        return JsonResponse({'success': True, 'matrix': normalized})

    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': 'Invalid JSON', 'details': str(e)}, status=400)
    except Exception as e:
        logger.error('roles/permissions error: %s', e, exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error', 'details': str(e)}, status=500)

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
    
    company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
    if not company:
        return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)

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
        
        # Get target user scoped to company
        try:
            target_user = User.objects.get(id=int(user_id), company=company)
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
    Enterprise Users API - Create a new user with multi-tenancy and branch assignment
    Admin-only. Accepts form-encoded or JSON.
    Fields: username, email, first_name, last_name, phone_number, role, primary_branch, 
            password (optional), send_invitation, force_password_change
    """
    from .forms import EnterpriseUserCreationForm
    from tenancy.models import Branch, UserBranch
    from audit.utils import log_audit
    
    # Optional: Import Alert if alerts app exists
    try:
        from alerts.models import Alert
        ALERTS_AVAILABLE = True
    except ImportError:
        Alert = None
        ALERTS_AVAILABLE = False
        logger.warning('Alerts app not available - user creation will proceed without alerts')
    
    # Resolve company context
    company = getattr(request, 'company', None) or getattr(request.user, 'company', None)

    # Authn
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    # Authz: use RolePermissionMatrix via users.utils.can so any role with
    # "manage_users" permission (typically Admin, optionally Manager) can
    # create users in their company. This is more robust than relying only on
    # is_staff / is_superuser flags and aligns with enterprise RBAC.
    if not user_utils.can(request.user, 'manage_users'):
        return JsonResponse({'success': False, 'error': 'Staff privileges required'}, status=403)

    if not company:
        return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)

    try:
        # Parse payload
        if request.content_type == 'application/json':
            data = json.loads(request.body or '{}')
        else:
            data = request.POST.dict()

        # Use EnterpriseUserCreationForm for validation and creation
        form = EnterpriseUserCreationForm(
            data=data,
            company=company,
            created_by=request.user
        )
        
        if form.is_valid():
            with transaction.atomic():
                # Save user with branch assignment
                user = form.save()
                
                # Get the generated password if any
                generated_password = getattr(form, 'generated_password', None)
                
                # Get primary branch
                primary_branch = form.cleaned_data.get('primary_branch')
                
                # Log audit event
                log_audit(
                    request.user,
                    'user_created',
                    details=(
                        f"Admin {request.user.username} created user '{user.username}' "
                        f"with role '{user.get_role_display()}' in branch '{primary_branch.name if primary_branch else 'N/A'}'."
                    ),
                    company=company,
                    branch=primary_branch,
                    related_user=user,
                    metadata={
                        'created_by': request.user.pk,
                        'created_by_username': request.user.username,
                        'new_user_id': user.pk,
                        'new_user_username': user.username,
                        'new_user_email': user.email,
                        'new_user_role': user.role,
                        'primary_branch_id': primary_branch.pk if primary_branch else None,
                        'primary_branch_name': primary_branch.name if primary_branch else None,
                        'invitation_sent': form.cleaned_data.get('send_invitation', False),
                    }
                )
                
                # Create welcome alert for new user (if alerts app is available)
                if primary_branch and ALERTS_AVAILABLE:
                    try:
                        Alert.objects.create(
                            company=company,
                            branch=primary_branch,
                            recipient=user,
                            level=Alert.LEVEL_INFO,
                            message=(
                                f"Welcome to {company.name}! Your account has been created. "
                                f"Your primary branch is '{primary_branch.name}'."
                            ),
                            context={
                                'user_id': user.pk,
                                'username': user.username,
                                'role': user.role,
                                'branch_id': primary_branch.pk,
                                'branch_name': primary_branch.name,
                                'created_by': request.user.pk,
                                'created_by_name': request.user.get_full_name() or request.user.username,
                            }
                        )
                    except Exception as alert_error:
                        # Log but don't fail user creation if alert fails
                        logger.warning(f'Failed to create welcome alert: {alert_error}')
            
            return JsonResponse({
                'success': True,
                'message': 'User created successfully with branch assignment',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name(),
                    'phone_number': user.phone_number,
                    'role': user.role,
                    'role_display': user.get_role_display(),
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'company_id': user.company_id,
                    'company_name': company.name,
                    'primary_branch_id': primary_branch.pk if primary_branch else None,
                    'primary_branch_name': primary_branch.name if primary_branch else None,
                },
                'temporary_password': generated_password,
                'invitation_token': user.invitation_token if user.is_invited else None,
                'force_password_change': user.force_password_change,
            })
        else:
            # Form validation failed - return errors
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }, status=400)
            
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
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)

        user = User.objects.select_related('company').prefetch_related(
            'user_branches__branch'
        ).get(id=user_id, company=company)
        
        # Determine user role
        if user.is_superuser:
            role = 'Admin'
        elif user.is_staff:
            role = 'Manager'
        else:
            role = 'User'
        
        # Get primary branch information
        branch_id = None
        branch_name = None
        primary_branch_rel = user.user_branches.filter(is_primary=True).first()
        if primary_branch_rel and primary_branch_rel.branch:
            branch_id = primary_branch_rel.branch.id
            branch_name = primary_branch_rel.branch.name
        
        # Get additional user info
        initials = ''
        if user.first_name and user.last_name:
            initials = f"{user.first_name[0]}{user.last_name[0]}".upper()
        elif user.username:
            initials = user.username[:2].upper()
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.username,
                'initials': initials,
                'role': role,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'branch_id': branch_id,
                'branch_name': branch_name,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'is_online': False  # Can be enhanced with session tracking
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

@api_admin_required
@require_http_methods(["POST", "PUT"])
@csrf_protect
def api_user_update(request, user_id):
    """
    Enterprise API - Update user details (Admin only)
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        
        # Get company context
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)
        
        # Get user (ensure same company)
        user = User.objects.get(id=user_id, company=company)
        
        # Prevent self-demotion
        if user.id == request.user.id and 'role' in data:
            return JsonResponse({
                'success': False,
                'error': 'Cannot change your own role'
            }, status=400)
        
        # Update basic fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'email' in data:
            email = data['email'].strip().lower()
            # Check email uniqueness
            if User.objects.filter(email=email, company=company).exclude(id=user.id).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Email already exists'
                }, status=400)
            user.email = email

        if 'phone_number' in data:
            user.phone_number = str(data['phone_number']).strip()
        
        if 'username' in data:
            username = data['username'].strip()
            # Check username uniqueness within company (multi-tenancy)
            if User.objects.filter(username=username, company=company).exclude(id=user.id).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Username already exists in your organization'
                }, status=400)
            user.username = username
        
        # Update role
        if 'role' in data:
            role = data['role'].lower()
            if role == 'admin':
                user.is_superuser = True
                user.is_staff = True
                if hasattr(user, 'role'):
                    user.role = 'admin'
            elif role == 'manager':
                user.is_superuser = False
                user.is_staff = True
                if hasattr(user, 'role'):
                    user.role = 'manager'
            else:  # user
                user.is_superuser = False
                user.is_staff = False
                if hasattr(user, 'role'):
                    user.role = 'user'
        
        # Update primary branch (with multi-tenancy validation)
        if 'branch_id' in data:
            from tenancy.models import Branch, UserBranch
            if data['branch_id']:
                try:
                    # Ensure branch belongs to same company (multi-tenancy)
                    branch = Branch.objects.get(id=data['branch_id'], company=company)
                    
                    # Remove old primary branch
                    UserBranch.objects.filter(user=user, company=company, is_primary=True).update(is_primary=False)
                    
                    # Set new primary branch
                    user_branch, created = UserBranch.objects.get_or_create(
                        user=user,
                        branch=branch,
                        company=company,
                        defaults={'is_primary': True}
                    )
                    if not created:
                        user_branch.is_primary = True
                        user_branch.save()
                        
                except Branch.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid branch selection'
                    }, status=400)
            else:
                # Remove primary branch assignment
                UserBranch.objects.filter(user=user, company=company, is_primary=True).update(is_primary=False)
        
        # Update active status (WORLD-CLASS: Require reason for status changes)
        if 'is_active' in data:
            # Prevent self-deactivation
            if user.id == request.user.id and not data['is_active']:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot deactivate your own account'
                }, status=400)
            
            # Check if status is actually changing
            new_status = bool(data['is_active'])
            if new_status != user.is_active:
                # WORLD-CLASS: Require reason for status change
                reason = data.get('status_change_reason', '').strip()
                if not reason:
                    return JsonResponse({
                        'success': False,
                        'error': 'Reason is required when changing account status',
                        'field': 'status_change_reason'
                    }, status=400)
                
                if len(reason) < 10:
                    return JsonResponse({
                        'success': False,
                        'error': 'Reason must be at least 10 characters',
                        'field': 'status_change_reason'
                    }, status=400)
                
                # Log status change with reason (separate audit event for importance)
                status_text = 'activated' if new_status else 'deactivated'
                AuditEvent.objects.create(
                    user=request.user,
                    company=company,
                    action=f'USER_{status_text.upper()}',
                    description=f'User account {status_text}: {user.username} - Reason: {reason}',
                    severity='CRITICAL',  # Critical severity for account status changes
                    metadata={
                        'user_id': user.id,
                        'username': user.username,
                        'full_name': user.get_full_name(),
                        'previous_status': user.is_active,
                        'new_status': new_status,
                        'reason': reason,
                        'changed_by': request.user.username
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    related_user=user
                )
            
            user.is_active = new_status
        
        user.save()
        
        # Refresh from database to get updated relationships
        user.refresh_from_db()
        
        # Log the action (AuditEvent already imported at top of file)
        AuditEvent.objects.create(
            user=request.user,
            company=company,
            action='USER_UPDATED',
            description=f'Updated user: {user.username}',
            metadata={
                'user_id': user.id,
                'username': user.username,
                'changes': data
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            related_user=user
        )
        
        # Get primary branch information for response
        branch_id = None
        branch_name = None
        primary_branch_rel = user.user_branches.filter(is_primary=True).first()
        if primary_branch_rel and primary_branch_rel.branch:
            branch_id = primary_branch_rel.branch.id
            branch_name = primary_branch_rel.branch.name
        
        # Determine role for response
        if user.is_superuser:
            role = 'Admin'
        elif user.is_staff:
            role = 'Manager'
        else:
            role = 'User'
        
        return JsonResponse({
            'success': True,
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name() or user.username,
                'role': role,
                'is_active': user.is_active,
                'branch_id': branch_id,
                'branch_name': branch_name
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_admin_required
@require_http_methods(["DELETE", "POST"])
@csrf_protect
def api_user_delete(request, user_id):
    """
    Enterprise API - Delete/deactivate user (Admin only)
    """
    try:
        # Get company context
        company = getattr(request, 'company', None) or getattr(request.user, 'company', None)
        if not company:
            return JsonResponse({'success': False, 'error': 'Company context required.'}, status=403)
        
        # Get user (ensure same company)
        user = User.objects.get(id=user_id, company=company)
        
        # Prevent self-deletion
        if user.id == request.user.id:
            return JsonResponse({
                'success': False,
                'error': 'Cannot delete your own account'
            }, status=400)
        
        # Check if permanent delete or deactivate
        permanent = request.GET.get('permanent', 'false').lower() == 'true'
        
        if permanent:
            # Permanent deletion (use with caution)
            username = user.username
            user.delete()
            action = 'USER_DELETED'
            message = f'User {username} permanently deleted'
        else:
            # Soft delete (deactivate)
            user.is_active = False
            user.save()
            action = 'USER_DEACTIVATED'
            message = f'User {user.username} deactivated'
        
        # Log the action (AuditEvent already imported at top of file)
        AuditEvent.objects.create(
            user=request.user,
            company=company,
            action=action,
            severity='WARNING' if action == 'USER_DELETED' else 'INFO',
            description=message,
            metadata={
                'user_id': user_id,
                'username': username if permanent else user.username,
                'permanent': permanent
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            related_user=user if not permanent else None
        )
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
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
