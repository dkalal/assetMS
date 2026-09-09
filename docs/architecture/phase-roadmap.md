# Staged Architecture Roadmap

Each phase is independently reviewable, reversible and deployable. A phase starts only after the previous phase's tests, migration checks and security gates are green.

## Phase 0A — Baseline stability

CI on PostgreSQL, maintained tests, transaction-safe approvals, self-approval denial and reliable tenant-aware fixtures. Delivered in PR #2.

## Phase 0B — Contract and guardrails

Freeze lifecycle/RBAC/tenancy/identifier/offline decisions in code and documentation. Remove permissive branch fallbacks, add cross-tenant denial tests and system checks. No schema migrations.

Rollback: revert application-only commits. No database rollback is required.

## Phase 1 — Additive tenancy and identity schema

Add `TenantMembership`, fixed role memberships, branch grants, opaque QR tokens, schema versions, concurrency versions and idempotency records. Keep legacy `User.company`, `User.role`, existing identifiers and statuses readable during dual-write.

Migration sequence:

1. add nullable/new tables and indexes concurrently where supported;
2. backfill memberships and role mappings in bounded, resumable batches;
3. backfill legacy `AuditLog.company` values, then validate counts, orphans,
   duplicate identifiers and cross-tenant relations;
4. enable dual-read/dual-write behind feature flags;
5. enforce new constraints only after validation.

Rollback: disable feature flags and return to legacy reads. Do not drop legacy columns or reverse destructive backfills in this phase.

## Phase 2 — Asset registration and acquisition

Implement request/planning approval, receiving references, serialized bulk creation, category schema snapshots and audited Tenant Admin direct registration. Registration may initiate a pending recipient handover.

## Phase 3 — Custody and handover

Implement recipient acceptance/rejection, required rejection reason/condition disagreement, checklist, accessories, notes and optional photos. Returned assets enter inspection. Emergency forced transfer stays out of scope.

## Phase 4 — Maintenance

Implement the work-order state machine, internal technician/external vendor assignment, completion verification, one-active-work-order constraint and idempotent preventive generation. Detailed labor/parts/invoice costing remains out of scope.

## Phase 5 — Loss, retirement and disposal

Implement employee loss reports plus manager confirmation, recovery inspection, separate retirement/disposal cases, policy-based approval and universal evidence. Preserve soft-deleted records indefinitely.

## Phase 6 — RBAC cutover

Switch authorization to fixed membership roles and delegated permission registry. Enforce Asset Manager tenant scope, Branch Manager assigned-branch scope, technician work scope and custodian self scope. Add expiring, reason-bound, audited platform support sessions.

## Phase 7 — Offline/PWA

Deliver encrypted tenant-separated caches, device registration/revocation, idempotent command sync, entity versions and supervisor conflict resolution for personal devices.

## Phase 8 — Operational workspace and Tailwind

Incrementally replace workflow screens with a responsive Tailwind system: dense desktop tables, mobile cards/drawers, QR-first actions and one asset operational workspace for summary, custody, maintenance, history, documents and actions. English is the initial UI language.

## Phase 9 — Scale and assurance

Validate tenants with 10,000–100,000 assets using query budgets, pagination, asynchronous exports, index analysis, backup/restore drills, security review, accessibility tests and ISO 55001-aligned evidence mapping without certification claims.
