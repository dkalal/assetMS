# Phase 0B Architecture Contract and Security Guardrails

Status: accepted implementation contract for the staged redesign. Phase 0B must not add or alter database migrations.

## Product boundary

AssetMS manages individually controlled assets of tenant-defined types. A bulk registration with quantity `N` creates `N` individual asset records so custody, condition, maintenance, loss and disposal remain independently auditable. Consumable inventory is a separate future bounded context.

The product lifecycle starts with a request, but Phase 1 does not implement purchase orders. The first acquisition slice is request/planning, approval, receiving/vendor/reference details and asset registration. Donations, leases, rentals and transferred-in acquisition methods remain out of the initial release.

Tenant Admin may register directly, with an immutable audit event. Branch Manager or Asset Manager approves ordinary asset plans within their scope. Receiving inspection is optional. Registration may nominate a recipient, but it creates a pending handover; custody does not move until that recipient accepts.

## Aggregate boundaries

| Aggregate | Owns | Does not own |
|---|---|---|
| Asset Request | business need, requester, branch, approval, fulfilment link | operational asset status |
| Asset | tenant, branch, category/schema version, identifiers, operational state | approval history and mutable user role |
| Custody Handover | sender, proposed recipient, checklist, accessories, notes, optional photos, acceptance/rejection | asset disposal |
| Maintenance Work Order | request-to-close workflow, technician/vendor, verification | procurement invoice and detailed costing in initial release |
| Disposal Case | request, approval policy snapshot, method, evidence, completion | soft deletion |
| Audit Event | actor, tenant, branch, action, target, before/after, request/device context | mutable business state |

All state-changing services lock the aggregate row, validate the expected version/state and write business state plus audit event in one database transaction. Retried API/offline commands use an idempotency key.

## Asset lifecycle

The executable source is `assets.domain_contract.ASSET_TRANSITIONS`.

| State | Meaning | Key exits |
|---|---|---|
| `draft` | registration is incomplete | available, pending acceptance |
| `available` | owned and ready for assignment/use | pending acceptance, maintenance, lost, retired |
| `pending_acceptance` | recipient has been nominated; custody has not moved | assigned on accept, available on reject/cancel |
| `assigned` | an employee has accepted custody | inspection, maintenance, lost, retired |
| `inspection_required` | returned or recovered and blocked from service | available, maintenance, retired |
| `in_maintenance` | one active work order controls serviceability | available/assigned after verification, inspection, retired |
| `lost` | reported and confirmed lost/stolen | inspection on recovery, retired |
| `retired` | removed from use but still owned | inspection/reactivation, disposal pending |
| `disposal_pending` | disposal awaits approval/completion | retired on rejection/cancel, disposed |
| `disposed` | ownership ended; terminal | none |

Soft deletion is not an asset status. It is administrative record visibility metadata and is retained indefinitely unless a lawful privacy deletion process applies. Retired and disposed identifiers are never reusable.

Return from custody and recovery from loss always enter `inspection_required`. Maintenance follows `requested → triaged → approved → scheduled → in_progress → completed → verified → closed`; only one non-terminal work order may exist per asset. Preventive schedules should create work orders asynchronously and idempotently through Celery in a later implementation phase.

## Roles and scopes

Roles are fixed; Tenant Admin may delegate only registered permissions and cannot invent roles.

| Role | Data scope | Product responsibility |
|---|---|---|
| Platform Super Admin | no tenant access by default | platform operations; support access later requires tenant, reason, expiry and audit |
| Tenant Admin | tenant-wide | tenant users/settings, policy and final high-risk actions |
| Asset Manager | tenant-wide | asset portfolio, lifecycle policy and cross-branch operations; no tenant IAM/settings by default |
| Branch Manager | explicitly assigned branches only | branch requests, handovers, maintenance and stocktake; never tenant-wide fallback |
| Technician | assigned work/branches | maintenance execution and permitted stocktake |
| Custodian/Employee | self and assets in their custody | accept/reject handover, request maintenance, report loss |

This is the required distinction: Asset Manager is a portfolio function across the tenant; Branch Manager is an operational owner restricted to named branches. The legacy `manager` role maps to Branch Manager during migration unless an explicit, audited promotion maps that membership to Asset Manager.

## Tenant isolation invariants

1. Every tenant-owned row has one non-null tenant key after migration.
2. Repository/query services require tenant context and fail closed when it is absent.
3. A URL/body tenant or branch identifier never establishes authorization; it is intersected with the authenticated membership scope.
4. Related objects must share the same tenant, validated in services and backed by database constraints where PostgreSQL permits.
5. Branch Manager with zero assignments sees zero tenant records.
6. Platform support has no implicit superuser tenant bypass.
7. Exports, tasks, cache keys, files, search and audit queries carry tenant scope.
8. Cross-tenant denial tests are mandatory for every new endpoint and background task.

## Identifiers and category schemas

- Manufacturer serial and asset tag are optional but unique per tenant across active, lost, retired, disposed and soft-deleted records.
- QR uses a high-entropy opaque token. Numeric database IDs never appear in public QR lookup. Token rotation invalidates the previous token and is audited.
- Similarity matches warn but do not block an individual save. Exact duplicates inside one bulk file block that import before writes begin.
- A category change does not reinterpret old dynamic data silently. Each asset retains an immutable schema-version snapshot. Moving to a new category/schema requires an explicit mapping operation with before/after audit data.
- QR generation may be asynchronous and does not block `available`; a trackable asset tag is required before physical handover. Public QR behaviour is tenant-configurable and, when enabled, exposes only asset tag/category plus tenant return phone/email.

## Disposal and evidence

The default approver is Tenant Admin. A later policy table may route by category and value; the chosen rule and approver are snapshotted on the disposal case. The universal minimum evidence is disposal method, date, reason, approver and completion note. One optional attachment supports receipt/certificate/photo. A data-wipe attestation becomes mandatory only for categories marked data-bearing.

## Offline and personal-device security

Offline scan, registration, stocktake, handover and maintenance commands are queued locally with idempotency keys and the last server entity version. Server state is authoritative. Version conflicts affecting custody or lifecycle never use last-write-wins; they enter a supervisor resolution queue with both versions preserved.

Personal-device support requires device registration, short-lived access tokens, encrypted local storage, tenant-separated caches, cached-data expiry, remote session revocation, minimal offline fields and an audit record for sync/device context. Public QR data must never seed authenticated offline caches.

## Retention

Business lifecycle, approval and custody audit records live for the tenant lifetime plus any legal hold. Authentication/security telemetry has a separate configurable retention: default 365 days, minimum 90 days. Purging is a scheduled, tenant-aware, audited process; identifiers and business audit are not recycled by that purge.

## Definition of done for Phase 0B

- this contract is executable and validated by tests;
- tenant and branch authorization helpers fail closed;
- cross-tenant regression tests cover branch decorators and queryset scope;
- Django system checks assert tenant keys/queryset scopes on critical models;
- the complete maintained suite passes on PostgreSQL CI;
- `makemigrations --check --dry-run` reports no changes.
