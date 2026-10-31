# Phase 1: Platform foundation

**Release:** R1 | **SRS:** API-01 to API-07, BE-20.1, BE-15.4, NFR-M2, section 3.3 rule 7 | **Owner:** Israel | **Size:** M | **Depends on:** 0

## Goal
Build the shared plumbing every later module uses: the `/api/v1/` surface, one error shape, pagination, idempotency, throttling, feature flags, central configuration and the immutable audit log. **Legacy routes must not change.**

## Read first
`docs/API_CONVENTIONS.md`, `docs/DECISIONS.md` (D-4, D-11), `docs/AUDIT.md`.

## Tasks
- [ ] **1.1 App `common`.** Create a new app named `common` (never `platform`, it clashes with the Python standard library). Add to `INSTALLED_APPS`.
- [ ] **1.2 `/api/v1/` root.** One include in `uniben_portal/urls.py`; each feature app plugs in its own v1 urls. Base API view sets `IsAuthenticated` by default; public endpoints are marked explicitly.
- [ ] **1.3 Error shape (API-06).** Custom exception handler applied **only to v1 views**, returning `code`, `message`, `field_errors`, `request_id`. Request-ID middleware adds the ID to logs and the response header.
- [ ] **1.4 Pagination (API-03).** Implement the pattern chosen in D-4; document it in `API_CONVENTIONS.md`.
- [ ] **1.5 Idempotency (API-04).** `IdempotencyKey` model (user, endpoint, key, response snapshot, created_at) and a reusable helper or decorator. Replay returns the stored response; a different request body with the same key returns 409.
- [ ] **1.6 Throttling (API-07).** DRF throttle classes for v1 with scopes: `default`, `auth`, `competitive`. Do **not** change global throttling for legacy views.
- [ ] **1.7 Feature flags.** `FeatureFlag` model (name, enabled, audience: all, cohort or department list) and `is_enabled(flag, user)`. Admin-editable. Seed all R2 and R3 flags **off**.
- [ ] **1.8 Configuration + audit (BE-20.1, BE-15.4).** `PlatformSetting` (key, JSON value, updated_by, updated_at) with every change written to an append-only `AuditLog` (actor, action, target, before/after, reason, request_id, created_at). No update or delete path in application code; read-only in Django admin.
- [ ] **1.9 Health.** `GET /api/v1/health` (public, no DB) and `GET /api/v1/ready` (checks DB).

## Tests required
Error shape on v1 only (legacy unchanged); pagination boundaries; idempotent replay and body-mismatch conflict; flag audience logic; audit rows cannot be updated or deleted through the model API; v1 default requires auth.

## Acceptance
A sample v1 endpoint returns the standard error shape, paginates, is authenticated by default, throttles, and its settings change is audited.

## Do not
Rename or alter legacy routes or responses; add Redis or Celery here; add third-party packages without asking.

## Start prompt
> Read CLAUDE.md, docs/API_CONVENTIONS.md and docs/phases/phase-01-platform-foundation.md. First ask me to settle D-4 (pagination). Then plan tasks 1.1 to 1.9 and wait for approval.
