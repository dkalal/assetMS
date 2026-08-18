# UI architecture inventory

Updated: 2026-08-18

## Active and required

- templates/base_dashboard.html is the authenticated base for dashboard, assets, transfers, maintenance, approvals, reports, audit, settings, users, and system administration.
- templates/components/auth_navbar_enhanced.html and templates/components/sidebar_enhanced.html are the active shell partials.
- templates/base_auth.html is the canonical login, registration, invitation, verification, and password-flow shell. No active template uses the retired templates/base.html compatibility shell.
- Active named variants selected by views include asset_detail_enhanced.html, asset_scan_enterprise.html, audit_dashboard_worldclass.html, reports_dashboard_worldclass.html, approval_dashboard_worldclass.html, and help_center_worldclass.html.
- Active administration surfaces now include the canonical user directory/staff profile, settings hub, organization profile, session center, security center, and category center.
- The canonical authenticated load path is Bootstrap, ui-foundation.css, app-shell.css, optional page CSS, and page JavaScript. Existing integration endpoints and DOM hooks remain authoritative.

## Active but compatibility-scoped

- No application page overrides the historical dashboard_content block; only base_dashboard.html defines the compatibility extension point.
- The active scanner now uses asset-scanner.css and asset-scanner.js; it no
  longer loads enterprise.css or scanner-worldclass.css.

## Legacy but still referenced

- enterprise.css and the former scanner helper assets have no active template
  references after scanner consolidation; they remain stored pending external-
  consumer deletion review.
- dashboard.css is referenced only by the shadowed app-level category template;
  the active project-level category template does not load it. The file remains
  stored pending legacy-template/external-consumer review.
- forms-worldclass.css and wizard-worldclass.css remain stored only for the
  retained legacy registration template; the historical URL now redirects to
  the canonical permission-aware registration workflow.
- Page-specific worldclass styles remain active only where an active template explicitly loads them.

## Apparently unused and requiring verification

- Remaining variants not yet classified should be retired only after the same route, template-origin and exact-reference checks.
- Category legacy variants and their dedicated wizard/editor assets were removed after route, filename-reference, template-loader, and regression verification.
- Active views still deliberately select several enterprise/enhanced/worldclass filenames; the filename alone is not evidence that a file is legacy.

The legacy public base, its override/table/theme assets, phase-2 backups, stale help duplicates, unused examples, old shell partials, and verified asset/approval/retirement variants were removed after repository-wide reference checks and focused regression coverage. Other candidates still require route rendering, static-reference verification, and regression coverage.

## Safe consolidation completed

- One canonical token namespace with Bootstrap and temporary legacy aliases.
- One navbar height, sidebar width, desktop content offset, 992px navigation boundary, backdrop, and shell controller.
- One active asset-list stylesheet/controller replacing page-inline code and duplicate asset-list controllers.
- Shared page header, form section/grid, error summary, sticky action bar, table shell, empty state, status badge, filter, selection, pagination, summary, panel, and record patterns.
- Authenticated UUID asset detail uses a compact operational view; anonymous QR access uses a separate minimal public template without sensitive operational fields.
- Transfer dashboard uses shared responsive patterns while retaining existing APIs, approval states, and permission checks.
- Maintenance list uses desktop tables and mobile records while preserving schedule, start, complete, and cancel POST contracts.
- Approval dashboard/detail use canonical queues, summaries, status badges, decision history, and responsive review actions.
- Employee retirement and retirement approval pages use canonical layouts and named API URLs supplied by templates.
- Asset create/edit uses one responsive, server-backed form layout with direct identifiers, category fields, assignment, customer linkage, maintenance planning, lifecycle details, approval context, accessible errors, duplicate feedback, and sticky actions.
- Dedicated asset creation/disposal requests use the same form primitives and retain their existing POST field names and route behavior.
- Page presentation and event handling for asset detail, transfer, maintenance, approvals, and retirements is extracted into page-scoped assets.
- Asset form, duplicate detection, and request-form enhancement code is extracted into scoped assets; the active form no longer loads duplicate-detection.js or asset-status-fields.js.
- Active reports and audit dashboards share one responsive records layer with compact summaries, filter grids, desktop tables, mobile records, empty states, and viewport-safe actions.
- Report generation retains its named POST endpoint, preview API, format/branch/status/date/person fields, hidden-frame download behavior, and role-scoped controls. Fake schedule/share/delete/bulk actions and random chart data were removed.
- Audit history retains company scoping, filters, pagination and asset links; it now uses server-backed values only and provides native print behavior rather than simulated exports/details.
- Users and access now use a responsive directory, mobile records, a canonical staff profile, semantic create/edit forms, and external scripts. Staff, security, access-log, and session APIs used by these screens are company scoped.
- Settings now exposes real profile, organization, security, session, and persisted system-setting workflows. Demo counters, random charts, and non-persistent save controls were removed.
- Category management now uses one compact category/field editor with Bootstrap modals, external assets, server validation, and company-scoped APIs. The unnecessary multi-step wizard was retired.
- Tenant setup, branch assignment, branch manager, manager performance, approval request, and the inactive approval variant now render through the canonical content block and app shell.
- Branch assignment and branch-manager administration share a responsive organization-admin layer; server-owned forms, admin RBAC, company scoping, audit behavior and notification behavior remain unchanged.
- Manager dashboard and performance report share a compact manager-center layer with mobile record layouts, external print behavior, and validated report periods. Invalid or unsupported period values now safely use 30 days.
- Active authentication flows use an isolated token-based shell. Login, registration, verification, invitation acceptance, password reset/change and logout retain their named URLs, POST fields, redirect field, CSRF and validation behavior.
- Help and resources now use a shared searchable support layer. The resources page lists only real named routes and hides the privileged import workflow from regular users.
- Maintenance scheduling now uses the canonical authenticated shell and responsive form primitives while retaining scheduled_for, supervisor and description POST fields.
- The historical integer asset-detail URL now performs its existing RBAC lookup
  and redirects to the canonical UUID detail URL. The stale integer detail
  template was removed, and retired/lost/deleted disposal redirects now resolve
  the UUID route correctly.
- The historical registration-wizard URL remains named for bookmark
  compatibility but redirects to the canonical asset form, which owns tenant
  scoping, admin direct creation, and manager approval behavior.
- Self-service transfer requests now load through active base-template blocks,
  use an unambiguous page reverse alias, receive the API URL from the template,
  and use a tokenized responsive stylesheet without production console output.
- System-administration dashboard, company list/create/detail, and impersonation
  confirmation use a shared scoped component layer. The previously missing
  impersonation confirmation template no longer produces a TemplateDoesNotExist
  500, and company suspension confirmation is unobtrusive JavaScript.
- System-administration company and user tables provide mobile record
  alternatives below 576px. Unmeasured database/Celery health placeholders
  were removed rather than presenting simulated operational status.
- The asset scanner uses scoped responsive assets, named lookup/list URLs,
  DOM-safe result/history rendering, accessible status announcements, and
  manual lookup when the camera library is unavailable.
- templates/base.html, global-override.css, enterprise-tables.css/js, theme-system.css, base.css, modal-zindex-fix.css and table-enhancer.js were retired after their final consumers were migrated.

## Migration verification notes

- AssetDetailByUUIDView is the active asset-detail implementation. Authenticated requests use asset_detail_enhanced.html; anonymous QR requests use asset_detail_public.html.
- ApprovalDashboardView selects approval_dashboard_worldclass.html. Approval decisions still POST to approval_action and retain company scoping, approver authority, and requester self-approval protection.
- Approval request detail now uses the canonical content block rather than the compatibility dashboard_content block.
- Retirement manager/admin scoping and administrator-only processing remain enforced by the existing decorators and service layer.
- Retirement status rendering now reads timeline and assets from the nested retirement response object used by the actual API.
- Retirement cancellation now uses the active api_retirement_cancel_mine endpoint.
- API-supplied retirement and transfer text is escaped before DOM insertion.
- Approval action logging no longer records POST payloads or decision notes.
- Existing stale asset-creation approval tests were aligned to the current assets URL namespace; endpoint names were not changed.
- Maintenance and transfer verification exposed stale task field names. Notification integrations were aligned to current models without changing lifecycle rules.
- Manager asset approvals accept both the active assigned_to field and the legacy assigned_to_id field. Direct identifiers, customer linkage, and maintenance configuration now survive approval metadata and approved asset creation.
- Dynamic category fields remain server-rendered for initial/edit/error states; JavaScript category refresh is progressive enhancement and the API remains company-scoped.
- The responsive Edge matrix includes asset create/edit and both related request forms. A diagnostic now reports the exact right-edge offender when overflow regresses.
- Audit free-text search now targets real Asset fields (asset_tag, serial_number and category) instead of the nonexistent asset.name lookup.
- Reports and audit no longer load dashboard-blue-modern.css, their legacy dashboard stylesheets, Chart.js, or inline event handlers.
- Login, registration and email-verification interactions are external scripts; password-required logout and logout confirmation remain native CSRF-protected POST forms.
- Maintenance schedule regression coverage performs a real service-backed POST and verifies the created date and supervisor, while confirming regular-user denial.
- Django template origin checks confirm project-level help, resources and maintenance templates are the active loader results.
- Exact reference checks found users/permission_groups.html and
  users/user_permissions.html have no active view or URL; they remain retained
  while template-checker coverage and any out-of-repository consumers are
  assessed.
- System-admin route tests cover global-operator access, company-admin denial,
  all six GET surfaces, CSRF presence, and the impersonation confirmation path.

## Deferred because of risk

- Removing the dashboard_content block definition from base_dashboard.html; it has no remaining consumers, but is retained for third-party/template-extension compatibility.
- Deleting remaining legacy or variant templates and static assets solely by filename.
- Deleting the retained registration wizard and orphan permission templates
  until external consumers and the template checker are updated independently.
- Reworking the global RolePermissionMatrix editor: its save payload replaces
  the complete matrix, so UI consolidation requires a separate permission-code
  inventory to guarantee no capabilities are dropped.
- Changing permission, tenancy, lifecycle, deletion/disposal, approval, transfer, or form field contracts.

## Recommended next migration order

1. Inventory every RolePermissionMatrix capability before externalizing or
   simplifying the global role editor.
2. Extend real-device camera testing beyond headless scanner layout checks.
3. Remove the retained wizard and orphan permission templates/assets only after
   external-consumer and template-checker verification.
4. Verify and retire the shadowed category template, dashboard.css, and the
   now-unreferenced enterprise/scanner helper assets.
