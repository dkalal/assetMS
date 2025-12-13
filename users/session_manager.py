"""
Enterprise Session Management Service
Handles advanced session operations with enterprise-grade features
"""
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import UserSession, AccessLog
import logging
import hashlib
from datetime import timedelta
from typing import Dict, List, Optional

User = get_user_model()
logger = logging.getLogger(__name__)

class EnterpriseSessionManager:
    """
    Enterprise-grade session management with advanced features:
    - Real-time session tracking
    - Concurrent session limits
    - Session analytics
    - Security monitoring
    - Automated cleanup
    """
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes
        self.max_concurrent_sessions = 10  # Per user limit
    
    def get_active_sessions(self, user_id: int = None, context: str = None) -> List[Dict]:
        """
        Get currently active sessions with real-time filtering
        Only returns sessions active within the last hour
        """
        cache_key = f"active_sessions_{user_id}_{context}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Define "active" as sessions with activity in the last hour
        active_threshold = timezone.now() - timedelta(hours=1)
        
        queryset = UserSession.objects.filter(
            is_active=True,
            last_activity__gte=active_threshold
        ).select_related('user')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if context:
            queryset = queryset.filter(session_context=context)
        
        sessions = []
        for session in queryset.order_by('-last_activity'):
            sessions.append({
                'id': session.id,
                'user_id': session.user.id,
                'username': session.user.username,
                'user_role': session.user.role,
                'session_context': session.session_context,
                'ip_address': session.ip_address,
                'browser_fingerprint': session.browser_fingerprint[:8],
                'created_at': session.created_at,
                'last_activity': session.last_activity,
                'duration_minutes': int((timezone.now() - session.created_at).total_seconds() / 60),
                'is_current_active': (timezone.now() - session.last_activity).total_seconds() < 300  # 5 min
            })
        
        cache.set(cache_key, sessions, self.cache_timeout)
        return sessions
    
    def get_session_statistics(self) -> Dict:
        """
        Get comprehensive session statistics for dashboard
        """
        cache_key = "session_statistics"
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        # Active sessions (last hour activity)
        active_sessions = UserSession.objects.filter(
            is_active=True,
            last_activity__gte=last_hour
        )
        
        # Session breakdown by context
        context_breakdown = {}
        for context_choice in UserSession.SESSION_CONTEXT_CHOICES:
            context = context_choice[0]
            count = active_sessions.filter(session_context=context).count()
            context_breakdown[context] = count
        
        # User role breakdown
        role_breakdown = {}
        for role_choice in User.ROLE_CHOICES:
            role = role_choice[0]
            count = active_sessions.filter(user__role=role).count()
            role_breakdown[role] = count
        
        # Concurrent sessions per user
        user_session_counts = {}
        for session in active_sessions.values('user_id', 'user__username'):
            user_id = session['user_id']
            username = session['user__username']
            if user_id not in user_session_counts:
                user_session_counts[user_id] = {'username': username, 'count': 0}
            user_session_counts[user_id]['count'] += 1
        
        max_concurrent = max([data['count'] for data in user_session_counts.values()]) if user_session_counts else 0
        avg_concurrent = sum([data['count'] for data in user_session_counts.values()]) / len(user_session_counts) if user_session_counts else 0
        
        stats = {
            'active_sessions_count': active_sessions.count(),
            'unique_active_users': active_sessions.values('user').distinct().count(),
            'sessions_today': UserSession.objects.filter(created_at__gte=last_24h).count(),
            'context_breakdown': context_breakdown,
            'role_breakdown': role_breakdown,
            'max_concurrent_per_user': max_concurrent,
            'avg_concurrent_per_user': round(avg_concurrent, 1),
            'users_with_multiple_sessions': len([u for u in user_session_counts.values() if u['count'] > 1]),
            'total_registered_users': User.objects.filter(is_active=True).count(),
            'last_updated': now.isoformat()
        }
        
        cache.set(cache_key, stats, 60)  # Cache for 1 minute
        return stats
    
    def terminate_session(self, session_id: int, reason: str = 'admin_terminated', 
                         terminated_by: User = None) -> bool:
        """
        Terminate a specific session with audit trail
        """
        try:
            with transaction.atomic():
                session = UserSession.objects.select_for_update().get(
                    id=session_id,
                    is_active=True
                )
                
                # Mark session as inactive
                session.is_active = False
                session.logout_reason = reason
                session.save()
                
                # Create audit log
                AccessLog.objects.create(
                    user=session.user,
                    action='logout',
                    ip_address=session.ip_address,
                    user_agent=session.user_agent,
                    details=f'Session terminated by {terminated_by.username if terminated_by else "system"}: {reason}'
                )
                
                # Clear related caches
                self._clear_session_caches(session.user.id)
                
                logger.info(f"Session {session_id} terminated by {terminated_by}: {reason}")
                return True
                
        except UserSession.DoesNotExist:
            logger.warning(f"Attempted to terminate non-existent session {session_id}")
            return False
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            return False
    
    def terminate_user_sessions(self, user_id: int, exclude_session_id: int = None, 
                               reason: str = 'admin_terminated', terminated_by: User = None) -> int:
        """
        Terminate all sessions for a user (except optionally one)
        """
        try:
            with transaction.atomic():
                queryset = UserSession.objects.filter(
                    user_id=user_id,
                    is_active=True
                )
                
                if exclude_session_id:
                    queryset = queryset.exclude(id=exclude_session_id)
                
                sessions = list(queryset.select_for_update())
                terminated_count = 0
                
                for session in sessions:
                    session.is_active = False
                    session.logout_reason = reason
                    session.save()
                    
                    # Create audit log for each session
                    AccessLog.objects.create(
                        user=session.user,
                        action='logout',
                        ip_address=session.ip_address,
                        user_agent=session.user_agent,
                        details=f'Session terminated by {terminated_by.username if terminated_by else "system"}: {reason}'
                    )
                    terminated_count += 1
                
                # Clear caches
                self._clear_session_caches(user_id)
                
                logger.info(f"Terminated {terminated_count} sessions for user {user_id}")
                return terminated_count
                
        except Exception as e:
            logger.error(f"Error terminating sessions for user {user_id}: {e}")
            return 0
    
    def cleanup_expired_sessions(self, hours_threshold: int = 24) -> int:
        """
        Clean up sessions that haven't been active for specified hours
        This addresses the "sessions counted after logout" issue
        """
        try:
            cutoff_time = timezone.now() - timedelta(hours=hours_threshold)
            
            # Find expired sessions
            expired_sessions = UserSession.objects.filter(
                last_activity__lt=cutoff_time,
                is_active=True
            )
            
            expired_count = expired_sessions.count()
            
            if expired_count > 0:
                # Mark as inactive with reason
                expired_sessions.update(
                    is_active=False,
                    logout_reason='expired_cleanup'
                )
                
                logger.info(f"Cleaned up {expired_count} expired sessions (older than {hours_threshold}h)")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0
    
    def cleanup_old_session_records(self, days_threshold: int = 30) -> int:
        """
        Permanently delete old session records for database maintenance
        Keeps audit trail but removes old inactive sessions
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days_threshold)
            
            # Delete old inactive sessions
            deleted_count = UserSession.objects.filter(
                last_activity__lt=cutoff_date,
                is_active=False
            ).delete()[0]
            
            if deleted_count > 0:
                logger.info(f"Permanently deleted {deleted_count} old session records (older than {days_threshold} days)")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during old session cleanup: {e}")
            return 0
    
    def enforce_concurrent_session_limit(self, user: User, current_session_id: int = None) -> int:
        """
        Enforce maximum concurrent sessions per user
        Terminates oldest sessions if limit exceeded
        """
        try:
            active_sessions = UserSession.objects.filter(
                user=user,
                is_active=True,
                last_activity__gte=timezone.now() - timedelta(hours=1)
            ).order_by('last_activity')
            
            if active_sessions.count() <= self.max_concurrent_sessions:
                return 0
            
            # Calculate how many to terminate
            excess_count = active_sessions.count() - self.max_concurrent_sessions
            sessions_to_terminate = active_sessions[:excess_count]
            
            terminated_count = 0
            for session in sessions_to_terminate:
                if current_session_id and session.id == current_session_id:
                    continue  # Don't terminate current session
                    
                session.is_active = False
                session.logout_reason = 'concurrent_limit'
                session.save()
                terminated_count += 1
            
            if terminated_count > 0:
                logger.info(f"Terminated {terminated_count} sessions for user {user.username} due to concurrent limit")
            
            return terminated_count
            
        except Exception as e:
            logger.error(f"Error enforcing session limit for user {user.id}: {e}")
            return 0
    
    def get_user_session_history(self, user_id: int, days: int = 7) -> List[Dict]:
        """
        Get session history for a user (for security monitoring)
        """
        since_date = timezone.now() - timedelta(days=days)
        
        sessions = UserSession.objects.filter(
            user_id=user_id,
            created_at__gte=since_date
        ).order_by('-created_at')
        
        history = []
        for session in sessions:
            history.append({
                'id': session.id,
                'session_context': session.session_context,
                'ip_address': session.ip_address,
                'browser_fingerprint': session.browser_fingerprint[:8],
                'created_at': session.created_at,
                'last_activity': session.last_activity,
                'is_active': session.is_active,
                'logout_reason': session.logout_reason,
                'duration_hours': round((session.last_activity - session.created_at).total_seconds() / 3600, 1)
            })
        
        return history
    
    def detect_suspicious_activity(self, user_id: int) -> Dict:
        """
        Detect potentially suspicious session activity
        """
        last_24h = timezone.now() - timedelta(hours=24)
        
        sessions = UserSession.objects.filter(
            user_id=user_id,
            created_at__gte=last_24h
        )
        
        # Analyze patterns
        unique_ips = sessions.values('ip_address').distinct().count()
        unique_browsers = sessions.values('browser_fingerprint').distinct().count()
        total_sessions = sessions.count()
        concurrent_sessions = sessions.filter(is_active=True).count()
        
        # Define suspicious thresholds
        suspicious_indicators = []
        
        if unique_ips > 5:
            suspicious_indicators.append(f"Multiple IP addresses ({unique_ips})")
        
        if unique_browsers > 3:
            suspicious_indicators.append(f"Multiple browsers ({unique_browsers})")
        
        if concurrent_sessions > 5:
            suspicious_indicators.append(f"High concurrent sessions ({concurrent_sessions})")
        
        if total_sessions > 20:
            suspicious_indicators.append(f"High session count ({total_sessions})")
        
        return {
            'is_suspicious': len(suspicious_indicators) > 0,
            'indicators': suspicious_indicators,
            'metrics': {
                'unique_ips': unique_ips,
                'unique_browsers': unique_browsers,
                'total_sessions_24h': total_sessions,
                'concurrent_sessions': concurrent_sessions
            }
        }
    
    def _clear_session_caches(self, user_id: int):
        """Clear session-related caches"""
        cache_patterns = [
            f"active_sessions_{user_id}_*",
            "session_statistics",
            f"user_sessions_{user_id}"
        ]
        
        for pattern in cache_patterns:
            cache.delete(pattern)
    
    def generate_session_report(self, days: int = 7) -> Dict:
        """
        Generate comprehensive session report for administrators
        """
        since_date = timezone.now() - timedelta(days=days)
        
        # Basic metrics
        total_sessions = UserSession.objects.filter(created_at__gte=since_date).count()
        active_sessions = UserSession.objects.filter(
            is_active=True,
            last_activity__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # User activity
        active_users = UserSession.objects.filter(
            last_activity__gte=timezone.now() - timedelta(hours=24)
        ).values('user').distinct().count()
        
        # Context breakdown
        context_stats = {}
        for context, _ in UserSession.SESSION_CONTEXT_CHOICES:
            count = UserSession.objects.filter(
                created_at__gte=since_date,
                session_context=context
            ).count()
            context_stats[context] = count
        
        # Security metrics
        failed_logins = AccessLog.objects.filter(
            action='failed_login',
            timestamp__gte=since_date
        ).count()
        
        return {
            'period_days': days,
            'total_sessions': total_sessions,
            'currently_active': active_sessions,
            'active_users_24h': active_users,
            'context_breakdown': context_stats,
            'failed_logins': failed_logins,
            'generated_at': timezone.now().isoformat()
        }

# Global instance
session_manager = EnterpriseSessionManager()