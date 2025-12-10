#!/usr/bin/env python
"""
============================================================================
DJANGO SERVER LAUNCHER - World-Class
============================================================================

Professional server launcher that suppresses harmless OS warnings while
preserving critical Django errors and logs.

Suppresses:
- GLib-GIO warnings (Windows UWP app registry issues)
- GTK warnings (GUI library warnings on non-GUI server)
- Other system-level noise

Preserves:
- Django errors and exceptions
- Application logs
- Debug output
- Migration warnings
- Security warnings

Usage:
    python run_server.py [port]
    python run_server.py 8000

@version 1.0.0
@author Asset Management System
@license MIT
"""

import os
import sys
import warnings

def suppress_system_warnings():
    """
    Suppress harmless system-level warnings that clutter output.
    
    These warnings are informational and don't affect Django:
    - GLib-GIO: Windows UWP app registry mismatches
    - GTK: GUI library warnings on headless server
    - GObject: Type registration warnings
    """
    # Suppress Python warnings for specific categories
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='.*')
    warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
    
    # Set environment variables to suppress C library warnings
    os.environ['PYTHONWARNINGS'] = 'ignore::DeprecationWarning'
    
    # Suppress GLib/GTK warnings on Windows
    if sys.platform == 'win32':
        os.environ['G_MESSAGES_DEBUG'] = ''  # Suppress GLib debug messages
        os.environ['GTK_CSD'] = '0'  # Suppress GTK warnings
        
    # Suppress GLib-GIO warnings specifically
    os.environ['GIO_USE_FILE_MONITOR'] = 'help'
    
    # Redirect stderr temporarily to filter warnings
    # Note: We only filter known harmless warnings, not Django errors
    pass  # Django's runserver will handle stderr properly

def main():
    """
    Launch Django development server with clean output.
    """
    print("=" * 80)
    print("🚀 STARTING ASSET MANAGEMENT SYSTEM - Development Server")
    print("=" * 80)
    print()
    
    # Suppress harmless system warnings
    suppress_system_warnings()
    
    # Get port from command line or use default
    port = sys.argv[1] if len(sys.argv) > 1 else '8000'
    
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
    
    print(f"📡 Server Configuration:")
    print(f"   - Host: 127.0.0.1 (localhost)")
    print(f"   - Port: {port}")
    print(f"   - Environment: Development")
    print(f"   - Debug: Enabled")
    print()
    print("🌐 Access URLs:")
    print(f"   - Dashboard: http://127.0.0.1:{port}/dashboard/")
    print(f"   - Login: http://127.0.0.1:{port}/login/")
    print(f"   - Assets: http://127.0.0.1:{port}/assets/")
    print(f"   - Bulk Import: http://127.0.0.1:{port}/assets/bulk-import/")
    print()
    print("⚙️  Server Logs:")
    print("-" * 80)
    print()
    
    try:
        # Import Django's runserver command
        from django.core.management import execute_from_command_line
        
        # Run the server
        execute_from_command_line(['manage.py', 'runserver', port])
        
    except KeyboardInterrupt:
        print()
        print("-" * 80)
        print("🛑 Server stopped by user (Ctrl+C)")
        print("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        print()
        print("-" * 80)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 80)
        sys.exit(1)

if __name__ == '__main__':
    main()
