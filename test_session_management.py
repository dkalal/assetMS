#!/usr/bin/env python
"""
Enterprise Session Management Test Script
Demonstrates the session management system functionality
"""
import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
django.setup()

from users.session_manager import session_manager
from users.models import User, UserSession, AccessLog
from django.contrib.auth import get_user_model

User = get_user_model()

class SessionManagementDemo:
    """Demonstrate enterprise session management features"""
    
    def __init__(self):
        self.demo_user = None
        self.created_sessions = []
    
    def setup_demo_data(self):
        """Create demo user and sessions for testing"""
        print("🔧 Setting up demo data...")
        
        # Create or get demo user
        self.demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'role': 'user',
                'is_active': True
            }
        )
        
        if created:
            self.demo_user.set_password('demo123')
            self.demo_user.save()
            print(f"✅ Created demo user: {self.demo_user.username}")
        else:
            print(f"✅ Using existing demo user: {self.demo_user.username}")
        
        # Create sample sessions with different contexts and timestamps
        session_data = [
            {
                'session_context': 'web',
                'ip_address': '192.168.1.100',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'browser_fingerprint': 'web_browser_001',
                'minutes_ago': 5  # Active session
            },
            {
                'session_context': 'mobile',
                'ip_address': '192.168.1.101',
                'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
                'browser_fingerprint': 'mobile_browser_001',
                'minutes_ago': 30  # Active session
            },
            {
                'session_context': 'web',
                'ip_address': '192.168.1.102',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'browser_fingerprint': 'web_browser_002',
                'minutes_ago': 90  # Should be considered inactive
            },
            {
                'session_context': 'api',
                'ip_address': '192.168.1.103',
                'user_agent': 'API Client v1.0',
                'browser_fingerprint': 'api_client_001',
                'minutes_ago': 1440  # 24 hours ago - expired
            }
        ]
        
        # Clean up existing demo sessions
        UserSession.objects.filter(user=self.demo_user).delete()
        
        # Create new demo sessions
        for data in session_data:
            last_activity = timezone.now() - timedelta(minutes=data['minutes_ago'])
            
            session = UserSession.objects.create(
                user=self.demo_user,
                session_key=f"demo_session_{data['session_context']}_{data['minutes_ago']}",
                session_context=data['session_context'],
                ip_address=data['ip_address'],
                user_agent=data['user_agent'],
                browser_fingerprint=data['browser_fingerprint'],
                is_active=True,
                created_at=last_activity,
                last_activity=last_activity
            )
            self.created_sessions.append(session)
        
        print(f"✅ Created {len(session_data)} demo sessions")
    
    def demonstrate_active_session_detection(self):
        """Show how the system detects truly active sessions"""
        print("\n🔍 DEMONSTRATING ACTIVE SESSION DETECTION")
        print("=" * 60)
        
        # Get all sessions for demo user
        all_sessions = UserSession.objects.filter(user=self.demo_user)
        print(f"📊 Total sessions in database: {all_sessions.count()}")
        
        # Show all sessions with their activity status
        print("\n📋 All Sessions:")
        for session in all_sessions:
            minutes_since_activity = (timezone.now() - session.last_activity).total_seconds() / 60
            is_considered_active = minutes_since_activity <= 60  # 1 hour threshold
            
            print(f"  • {session.session_context.upper()} | "
                  f"Last Activity: {int(minutes_since_activity)}m ago | "
                  f"Status: {'🟢 ACTIVE' if is_considered_active else '🔴 INACTIVE'}")
        
        # Use session manager to get only active sessions
        active_sessions = session_manager.get_active_sessions(user_id=self.demo_user.id)
        print(f"\n✅ Sessions considered ACTIVE by session manager: {len(active_sessions)}")
        
        for session_data in active_sessions:
            print(f"  • {session_data['session_context'].upper()} | "
                  f"Duration: {session_data['duration_minutes']}m | "
                  f"Currently Active: {'🟢 YES' if session_data['is_current_active'] else '🟡 IDLE'}")
    
    def demonstrate_session_statistics(self):
        """Show comprehensive session statistics"""
        print("\n📈 DEMONSTRATING SESSION STATISTICS")
        print("=" * 60)
        
        stats = session_manager.get_session_statistics()
        
        print("🎯 Key Metrics:")
        print(f"  • Active Sessions: {stats['active_sessions_count']}")
        print(f"  • Unique Active Users: {stats['unique_active_users']}")
        print(f"  • Sessions Created Today: {stats['sessions_today']}")
        print(f"  • Users with Multiple Sessions: {stats['users_with_multiple_sessions']}")
        print(f"  • Max Concurrent per User: {stats['max_concurrent_per_user']}")
        print(f"  • Avg Concurrent per User: {stats['avg_concurrent_per_user']}")
        
        print("\n📊 Context Breakdown:")
        for context, count in stats['context_breakdown'].items():
            print(f"  • {context.title()}: {count}")
        
        print("\n👥 Role Breakdown:")
        for role, count in stats['role_breakdown'].items():
            print(f"  • {role.title()}: {count}")
    
    def demonstrate_session_cleanup(self):
        """Show session cleanup functionality"""
        print("\n🧹 DEMONSTRATING SESSION CLEANUP")
        print("=" * 60)
        
        # Show sessions before cleanup
        before_count = UserSession.objects.filter(user=self.demo_user, is_active=True).count()
        print(f"📊 Active sessions before cleanup: {before_count}")
        
        # Run cleanup (mark sessions inactive after 1 hour)
        cleaned_count = session_manager.cleanup_expired_sessions(hours_threshold=1)
        print(f"🧹 Sessions marked as expired: {cleaned_count}")
        
        # Show sessions after cleanup
        after_count = UserSession.objects.filter(user=self.demo_user, is_active=True).count()
        print(f"📊 Active sessions after cleanup: {after_count}")
        
        # Show inactive sessions
        inactive_count = UserSession.objects.filter(user=self.demo_user, is_active=False).count()
        print(f"📊 Inactive sessions: {inactive_count}")
        
        print("\n💡 This demonstrates how the system addresses the 'session persistence after logout' issue!")
        print("   Sessions are marked as inactive but kept for audit purposes.")
    
    def demonstrate_suspicious_activity_detection(self):
        """Show suspicious activity detection"""
        print("\n🚨 DEMONSTRATING SUSPICIOUS ACTIVITY DETECTION")
        print("=" * 60)
        
        # Create additional sessions from different IPs to simulate suspicious activity
        suspicious_ips = ['10.0.0.1', '172.16.0.1', '203.0.113.1', '198.51.100.1', '192.0.2.1', '203.0.113.2']
        
        print("🔧 Creating sessions from multiple IPs to simulate suspicious activity...")
        for i, ip in enumerate(suspicious_ips):
            UserSession.objects.create(
                user=self.demo_user,
                session_key=f"suspicious_session_{i}",
                session_context='web',
                ip_address=ip,
                user_agent=f'Browser {i}',
                browser_fingerprint=f'suspicious_browser_{i}',
                is_active=True
            )
        
        # Analyze suspicious activity
        analysis = session_manager.detect_suspicious_activity(self.demo_user.id)
        
        print(f"\n🔍 Suspicious Activity Analysis:")
        print(f"  • Is Suspicious: {'🚨 YES' if analysis['is_suspicious'] else '✅ NO'}")
        
        if analysis['indicators']:
            print("  • Indicators:")
            for indicator in analysis['indicators']:
                print(f"    - {indicator}")
        
        print("\n📊 Metrics:")
        for metric, value in analysis['metrics'].items():
            print(f"  • {metric.replace('_', ' ').title()}: {value}")
    
    def demonstrate_session_termination(self):
        """Show session termination functionality"""
        print("\n🔌 DEMONSTRATING SESSION TERMINATION")
        print("=" * 60)
        
        # Get an active session to terminate
        active_sessions = session_manager.get_active_sessions(user_id=self.demo_user.id)
        
        if active_sessions:
            session_to_terminate = active_sessions[0]
            session_id = session_to_terminate['id']
            
            print(f"🎯 Terminating session: {session_to_terminate['session_context']} from {session_to_terminate['ip_address']}")
            
            # Terminate the session
            success = session_manager.terminate_session(
                session_id=session_id,
                reason='demo_termination',
                terminated_by=self.demo_user
            )
            
            if success:
                print("✅ Session terminated successfully")
                
                # Verify termination
                updated_sessions = session_manager.get_active_sessions(user_id=self.demo_user.id)
                print(f"📊 Active sessions after termination: {len(updated_sessions)}")
            else:
                print("❌ Failed to terminate session")
        else:
            print("ℹ️  No active sessions to terminate")
    
    def demonstrate_session_report(self):
        """Show session reporting functionality"""
        print("\n📋 DEMONSTRATING SESSION REPORTING")
        print("=" * 60)
        
        report = session_manager.generate_session_report(days=7)
        
        print("📈 7-Day Session Report:")
        print(f"  • Total Sessions: {report['total_sessions']}")
        print(f"  • Currently Active: {report['currently_active']}")
        print(f"  • Active Users (24h): {report['active_users_24h']}")
        print(f"  • Failed Logins: {report['failed_logins']}")
        
        print("\n📊 Context Breakdown:")
        for context, count in report['context_breakdown'].items():
            print(f"  • {context.title()}: {count}")
        
        print(f"\n🕒 Report Generated: {report['generated_at']}")
    
    def cleanup_demo_data(self):
        """Clean up demo data"""
        print("\n🧹 Cleaning up demo data...")
        
        # Delete demo sessions
        UserSession.objects.filter(user=self.demo_user).delete()
        
        # Delete demo user (optional - comment out to keep for further testing)
        # self.demo_user.delete()
        
        print("✅ Demo data cleaned up")
    
    def run_full_demo(self):
        """Run the complete demonstration"""
        print("🚀 ENTERPRISE SESSION MANAGEMENT SYSTEM DEMONSTRATION")
        print("=" * 80)
        print("This demo shows how the system addresses session persistence issues")
        print("and implements enterprise-grade session management features.")
        print("=" * 80)
        
        try:
            self.setup_demo_data()
            self.demonstrate_active_session_detection()
            self.demonstrate_session_statistics()
            self.demonstrate_session_cleanup()
            self.demonstrate_suspicious_activity_detection()
            self.demonstrate_session_termination()
            self.demonstrate_session_report()
            
            print("\n🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("Key Takeaways:")
            print("• Sessions are only considered 'active' if they have recent activity (< 1 hour)")
            print("• Expired sessions are marked inactive but kept for audit purposes")
            print("• The system provides comprehensive monitoring and control capabilities")
            print("• Security features detect and alert on suspicious activity")
            print("• Enterprise-grade performance with caching and optimization")
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Ask if user wants to keep demo data
            try:
                keep_data = input("\n🤔 Keep demo data for further testing? (y/N): ").lower()
                if keep_data != 'y':
                    self.cleanup_demo_data()
            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted by user")

def main():
    """Main function to run the demonstration"""
    demo = SessionManagementDemo()
    demo.run_full_demo()

if __name__ == '__main__':
    main()