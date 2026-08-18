"""Compile selected templates to detect TemplateSyntaxError without running the full test suite.

Run from project root with the virtualenv activated:
    python scripts/check_templates.py
"""
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import django
import os
from django.template import TemplateSyntaxError
from django.template.loader import get_template

TEMPLATES_TO_CHECK = [
    'base_dashboard.html',
    'base_auth.html',
    'components/profile_avatar.html',
    'components/auth_navbar_enhanced.html',
    'components/sidebar_enhanced.html',
    'users/user_permissions.html',
    'users/profile.html',
    'users/my_transfer_requests.html',
    'system_admin/dashboard.html',
    'system_admin/company_list.html',
    'system_admin/create_company.html',
    'system_admin/company_detail.html',
    'system_admin/impersonate_confirm.html',
    'system_admin/role_permissions.html',
    'assets/asset_scan_enterprise.html',
]


def main():
    # Ensure DJANGO_SETTINGS_MODULE is set to the project's settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assetms.settings')
    try:
        django.setup()
    except Exception as e:
        print('Django setup failed:', e)
        sys.exit(2)

    ok = True
    for tpl in TEMPLATES_TO_CHECK:
        try:
            t = get_template(tpl)
            # Force compilation by rendering with empty context where safe
            try:
                t.render({})
            except Exception:
                # rendering may fail due to missing context; that's OK for syntax check
                pass
            print(f'[OK] {tpl}')
        except TemplateSyntaxError as te:
            ok = False
            print(f'[ERROR] TemplateSyntaxError in {tpl}: {te}')
        except Exception as e:
            ok = False
            print(f'[ERROR] Failed loading {tpl}: {e}')

    if not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
