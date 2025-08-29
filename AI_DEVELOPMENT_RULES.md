# 🤖 AI Development Rules for Enterprise Asset Management System

## 📋 **Core Development Philosophy**

### **Rule 1: Start Small, Scale Smart**
- **Minimum Viable Changes**: Implement the smallest possible change that delivers value
- **Incremental Development**: Build features in small, testable increments
- **Risk Mitigation**: Reduce blast radius of changes through modular implementation
- **Validation First**: Prove concept with minimal code before expanding

### **Rule 2: Enterprise-First Mindset**
- **Security by Design**: Every change must consider security implications
- **Scalability Awareness**: Code must handle enterprise-scale data and users
- **Compliance Ready**: Maintain audit trails and regulatory compliance
- **Performance Conscious**: Consider performance impact of every change

## 🔒 **Security Rules**

### **Rule 3: Security is Non-Negotiable**
```python
# ✅ ALWAYS DO
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ❌ NEVER DO
SECRET_KEY = 'hardcoded-secret-key'
DEBUG = True  # in production
```

### **Rule 4: Input Validation Everywhere**
- **Server-Side Validation**: Never trust client-side validation alone
- **Sanitization**: Clean all user inputs before processing
- **Type Checking**: Validate data types and formats
- **SQL Injection Prevention**: Use parameterized queries only

### **Rule 5: Authentication & Authorization**
- **Role-Based Access**: Check permissions at every endpoint
- **Session Security**: Implement secure session management
- **Audit Logging**: Log all security-relevant actions
- **Fail Secure**: Default to deny access when in doubt

## 🏗️ **Architecture Rules**

### **Rule 6: Modular Design Principles**
```python
# ✅ Good: Modular, single responsibility
class AssetManager:
    def create_asset(self, data):
        # Single responsibility
        pass

# ❌ Bad: Monolithic, multiple responsibilities
class AssetEverything:
    def create_asset_and_send_email_and_log_and_validate(self):
        # Too many responsibilities
        pass
```

### **Rule 7: Database Design Excellence**
- **Normalization**: Follow 3NF principles for data integrity
- **Indexing Strategy**: Index frequently queried columns
- **Migration Safety**: Always create reversible migrations
- **Query Optimization**: Use select_related() and prefetch_related()

### **Rule 8: API Design Standards**
```python
# ✅ RESTful, predictable endpoints
GET    /api/assets/          # List assets
POST   /api/assets/          # Create asset
GET    /api/assets/{id}/     # Get specific asset
PUT    /api/assets/{id}/     # Update asset
DELETE /api/assets/{id}/     # Delete asset

# ❌ Inconsistent, unclear endpoints
GET /get_all_assets/
POST /create_new_asset_endpoint/
```

## 💻 **Code Quality Rules**

### **Rule 9: Clean Code Standards**
```python
# ✅ Clean, readable code
def calculate_asset_depreciation(asset, years):
    """Calculate straight-line depreciation for an asset."""
    if not asset.purchase_value or not years:
        return 0
    
    annual_depreciation = asset.purchase_value / years
    return annual_depreciation

# ❌ Unclear, hard to maintain
def calc(a, y):
    return a.pv / y if a.pv and y else 0
```

### **Rule 10: Error Handling Excellence**
```python
# ✅ Comprehensive error handling
try:
    asset = Asset.objects.get(id=asset_id)
    result = process_asset(asset)
    log_audit(user, 'process', asset, 'Asset processed successfully')
    return result
except Asset.DoesNotExist:
    logger.error(f"Asset {asset_id} not found")
    return JsonResponse({'error': 'Asset not found'}, status=404)
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    return JsonResponse({'error': str(e)}, status=400)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return JsonResponse({'error': 'Internal server error'}, status=500)
```

### **Rule 11: Testing Requirements**
- **Unit Tests**: Every function must have unit tests
- **Integration Tests**: Test component interactions
- **Security Tests**: Test authentication and authorization
- **Performance Tests**: Benchmark critical operations

## 🚀 **Performance Rules**

### **Rule 12: Database Optimization**
```python
# ✅ Optimized queries
assets = Asset.objects.select_related('category', 'assigned_to')\
                     .prefetch_related('audit_logs')\
                     .filter(status='active')

# ❌ N+1 query problem
assets = Asset.objects.filter(status='active')
for asset in assets:
    print(asset.category.name)  # Causes N+1 queries
```

### **Rule 13: Caching Strategy**
```python
# ✅ Strategic caching
from django.core.cache import cache

def get_user_permissions(user_id):
    cache_key = f"user_permissions_{user_id}"
    permissions = cache.get(cache_key)
    
    if permissions is None:
        permissions = calculate_permissions(user_id)
        cache.set(cache_key, permissions, timeout=3600)  # 1 hour
    
    return permissions
```

### **Rule 14: Frontend Performance**
```javascript
// ✅ Debounced search
class SearchManager {
    constructor() {
        this.searchTimeout = null;
        this.debounceDelay = 300;
    }
    
    search(query) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.performSearch(query);
        }, this.debounceDelay);
    }
}

// ❌ Immediate search on every keystroke
function search(query) {
    performSearch(query);  // Too frequent API calls
}
```

## 🔄 **Change Management Rules**

### **Rule 15: Incremental Implementation**
```
Phase 1: Core Functionality (Minimal Viable Feature)
├── Basic CRUD operations
├── Essential validation
└── Basic error handling

Phase 2: Enhancement (Value-Added Features)
├── Advanced validation
├── Performance optimization
└── User experience improvements

Phase 3: Enterprise Features (Advanced Capabilities)
├── Advanced security features
├── Integration capabilities
└── Analytics and reporting
```

### **Rule 16: Backward Compatibility**
- **API Versioning**: Version APIs to maintain compatibility
- **Database Migrations**: Never break existing data
- **Feature Flags**: Use feature toggles for gradual rollouts
- **Deprecation Strategy**: Provide migration paths for deprecated features

### **Rule 17: Documentation Requirements**
```python
def create_asset(category_id: int, data: dict, user: User) -> Asset:
    """
    Create a new asset with comprehensive validation and audit logging.
    
    Args:
        category_id: ID of the asset category
        data: Dictionary containing asset data
        user: User creating the asset
        
    Returns:
        Asset: The created asset instance
        
    Raises:
        ValidationError: If asset data is invalid
        PermissionError: If user lacks creation permissions
        
    Example:
        >>> asset = create_asset(1, {'name': 'Laptop'}, admin_user)
        >>> assert asset.category_id == 1
    """
```

## 🧪 **Testing Rules**

### **Rule 18: Test-Driven Development**
```python
# ✅ Write tests first
def test_asset_creation_with_valid_data():
    """Test that assets are created correctly with valid data."""
    category = AssetCategory.objects.create(name='Electronics')
    data = {'name': 'Test Laptop', 'serial_number': 'TL001'}
    
    asset = create_asset(category.id, data, self.admin_user)
    
    assert asset.category == category
    assert asset.dynamic_data['name'] == 'Test Laptop'
    assert asset.dynamic_data['serial_number'] == 'TL001'

# Then implement the function
def create_asset(category_id, data, user):
    # Implementation follows test requirements
    pass
```

### **Rule 19: Test Coverage Requirements**
- **Minimum Coverage**: 80% code coverage required
- **Critical Path Coverage**: 100% coverage for security-critical code
- **Edge Case Testing**: Test boundary conditions and error scenarios
- **Integration Testing**: Test complete user workflows

## 📊 **Monitoring Rules**

### **Rule 20: Observability First**
```python
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def monitor_performance(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper

@monitor_performance
def process_bulk_assets(assets):
    # Function implementation
    pass
```

### **Rule 21: Audit Everything**
```python
def log_audit(user, action, asset, details, **kwargs):
    """Log all significant system actions for compliance."""
    AuditLog.objects.create(
        user=user,
        action=action,
        asset=asset,
        details=details,
        metadata={
            'timestamp': timezone.now().isoformat(),
            'ip_address': kwargs.get('ip_address'),
            'user_agent': kwargs.get('user_agent'),
            'session_id': kwargs.get('session_id'),
        }
    )
```

## 🚀 **Deployment Rules**

### **Rule 22: Environment Separation**
```python
# settings/base.py - Common settings
# settings/development.py - Development overrides
# settings/production.py - Production overrides
# settings/testing.py - Testing overrides

# ✅ Environment-specific configuration
import os
from .base import *

if os.environ.get('ENVIRONMENT') == 'production':
    from .production import *
elif os.environ.get('ENVIRONMENT') == 'testing':
    from .testing import *
else:
    from .development import *
```

### **Rule 23: Zero-Downtime Deployments**
- **Blue-Green Deployments**: Maintain two identical production environments
- **Database Migrations**: Run migrations that are backward compatible
- **Feature Flags**: Control feature rollouts without code deployments
- **Health Checks**: Implement comprehensive health check endpoints

### **Rule 24: Rollback Strategy**
```python
# ✅ Always have a rollback plan
def deploy_new_feature():
    """
    Deployment checklist:
    1. Backup current database state
    2. Deploy code with feature flag OFF
    3. Run database migrations
    4. Verify system health
    5. Enable feature flag gradually
    6. Monitor metrics and errors
    7. Full rollback plan ready
    """
    pass
```

## 📚 **Enterprise Learning Principles**

### **Rule 25: Continuous Learning**
- **Code Reviews**: Learn from peer feedback on every change
- **Architecture Reviews**: Regular system architecture assessments
- **Security Reviews**: Periodic security audits and penetration testing
- **Performance Reviews**: Regular performance benchmarking

### **Rule 26: Knowledge Sharing**
```python
"""
Enterprise Development Patterns Used in This System:

1. Repository Pattern: Encapsulate data access logic
2. Factory Pattern: Create objects without specifying exact classes
3. Observer Pattern: Audit logging system
4. Strategy Pattern: Different authentication methods
5. Decorator Pattern: Permission checking and logging
6. Singleton Pattern: Cache managers and configuration
"""
```

## 🎯 **Implementation Priority Matrix**

### **Priority 1: Security & Stability**
1. Fix hardcoded secrets
2. Implement proper error handling
3. Add comprehensive logging
4. Secure all endpoints

### **Priority 2: Performance & Scalability**
1. Optimize database queries
2. Implement caching strategy
3. Add performance monitoring
4. Optimize frontend assets

### **Priority 3: Features & Enhancements**
1. Add new functionality
2. Improve user experience
3. Extend API capabilities
4. Add advanced reporting

## 🔧 **Development Workflow**

### **Rule 27: Standard Development Process**
```
1. Analysis Phase
   ├── Understand requirements
   ├── Identify affected components
   ├── Plan minimal implementation
   └── Define success criteria

2. Design Phase
   ├── Create technical design
   ├── Review security implications
   ├── Plan testing strategy
   └── Define rollback plan

3. Implementation Phase
   ├── Write tests first (TDD)
   ├── Implement minimal solution
   ├── Add comprehensive error handling
   └── Document changes

4. Validation Phase
   ├── Run all tests
   ├── Perform security review
   ├── Test performance impact
   └── Validate user experience

5. Deployment Phase
   ├── Deploy to staging
   ├── Run integration tests
   ├── Deploy to production
   └── Monitor metrics
```

## 📖 **Enterprise Patterns Reference**

### **Authentication & Authorization Patterns**
```python
# Role-Based Access Control (RBAC)
class RoleBasedPermissionMixin:
    def has_permission(self, user, action, resource):
        return user.role in self.get_allowed_roles(action, resource)

# Attribute-Based Access Control (ABAC)
class AttributeBasedPermissionMixin:
    def has_permission(self, user, action, resource, context):
        return self.evaluate_policy(user.attributes, action, 
                                  resource.attributes, context)
```

### **Data Access Patterns**
```python
# Repository Pattern
class AssetRepository:
    def find_by_category(self, category_id):
        return Asset.objects.filter(category_id=category_id)
    
    def find_active_assets(self):
        return Asset.objects.filter(status='active')

# Unit of Work Pattern
class UnitOfWork:
    def __init__(self):
        self._new_objects = []
        self._dirty_objects = []
        self._removed_objects = []
    
    def commit(self):
        with transaction.atomic():
            self._insert_new()
            self._update_dirty()
            self._delete_removed()
```

### **Caching Patterns**
```python
# Cache-Aside Pattern
def get_asset(asset_id):
    cache_key = f"asset_{asset_id}"
    asset = cache.get(cache_key)
    
    if asset is None:
        asset = Asset.objects.get(id=asset_id)
        cache.set(cache_key, asset, timeout=3600)
    
    return asset

# Write-Through Pattern
def update_asset(asset_id, data):
    asset = Asset.objects.get(id=asset_id)
    for key, value in data.items():
        setattr(asset, key, value)
    
    asset.save()
    cache.set(f"asset_{asset_id}", asset, timeout=3600)
    return asset
```

---

## 🎓 **Enterprise Development Education**

### **Key Concepts Demonstrated in This System**

1. **Domain-Driven Design (DDD)**
   - Clear domain boundaries (assets, users, audit)
   - Rich domain models with business logic
   - Ubiquitous language throughout codebase

2. **SOLID Principles**
   - Single Responsibility: Each class has one reason to change
   - Open/Closed: Extensible through inheritance and composition
   - Liskov Substitution: Derived classes are substitutable
   - Interface Segregation: Clients depend only on methods they use
   - Dependency Inversion: Depend on abstractions, not concretions

3. **Enterprise Integration Patterns**
   - Message Queue integration ready
   - Event-driven architecture with signals
   - API Gateway pattern for external integrations
   - Circuit Breaker pattern for resilience

4. **Security Patterns**
   - Defense in Depth: Multiple security layers
   - Principle of Least Privilege: Minimal required permissions
   - Secure by Default: Safe defaults for all configurations
   - Zero Trust Architecture: Verify everything, trust nothing

---

**Remember: These rules are living guidelines that evolve with the system. Always prioritize security, maintainability, and user value in every decision.**
