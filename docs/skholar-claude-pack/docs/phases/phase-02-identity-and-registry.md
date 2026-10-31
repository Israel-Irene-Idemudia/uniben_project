# Phase 2: Identity, accounts and registry

**Release:** R1 | **SRS:** BE-01, BE-02, DATA-01, DATA-02, DATA-17 | **Owner:** Israel | **Size:** L | **Depends on:** 1

## Goal
One account that works in Flutter and the web world, a clean faculty/department registry with history, safe account states, and the world hand-off token.

## Read first
`docs/DECISIONS.md` (D-3, D-8, D-13, D-15), `docs/AUDIT.md`.

## Tasks
- [ ] **2.1 Registry data check (read only).** Report duplicate faculty/department names and profiles with null faculty/department. Do not change data.
- [ ] **2.2 Registry fields (BE-02.1).** Additive migration: `code` and `is_active` on `Faculty` and `Department` (nullable first, backfill, then constraints only if the data check is clean). Admin management.
- [ ] **2.3 `StudentDepartmentHistory` (DATA-02).** (user, faculty, department, effective_from, effective_to, changed_by, reason). Backfill one row per existing profile. Past season results must keep using the department the student had at the time.
- [ ] **2.4 Profile endpoints (BE-02.3).** `GET/PATCH /api/v1/me` with public fields (display name, avatar reference, level, department, badges) and private fields (contact, real name) visible only to the student and admins. `GET /api/v1/me/progress` returns the agreed shape; fields depending on the ledger return placeholders until Phase 3 and are completed in Phase 4 (BE-02.4).
- [ ] **2.5 Department change (BE-02.2).** `POST /api/v1/me/department-change`: once per semester (D-3) unless an admin approves; writes history; never rewrites past results. Required at onboarding **for new registrations**; existing null profiles get a "complete your profile" state instead of a hard NOT NULL.
- [ ] **2.6 World hand-off (BE-01.3).** `POST /api/v1/auth/world-handoff` (authenticated) creates a one-time token (cryptographically random, only a hash stored, short life per D-8, single use, bound to the user). A second call exchanges it for a normal session. Never put the main JWT in a URL. Rate-limited and audited.
- [ ] **2.7 Session revocation (BE-01.2).** Revoke all outstanding refresh tokens on password change and on an admin action (use the existing blacklist app).
- [ ] **2.8 Rate limits, lockout and auth log (BE-01.4).** Apply to login, OTP and password reset per D-15, without breaking existing Flutter flows. `AuthEvent` model records attempts and outcomes.
- [ ] **2.9 Account states (BE-01.5, BE-01.6).** `active`, `suspended`, `deleted`. A permission class blocks suspended accounts from social and competitive features. Map the existing `AccountDeletionRequest` flow onto the `deleted` state with anonymisation that preserves ledger and audit integrity (DATA-17). Data export for the student's own record (Should).

## Tests required
Registry constraints; history backfill; department change rules (once per semester, admin override); hand-off token single use, expiry, wrong-user and replay; refresh tokens revoked on password change; lockout after the configured failures; suspended user blocked from a protected view; legacy `/api/token/` and `/api/accounts/` flows still pass.

## Acceptance (SRS)
A student registers in Flutter, opens the web world from the app and arrives signed in as the same student. Five failed logins trigger the back-off and appear in the auth log. Changing department moves future contributions only. The registry can be corrected in admin with no client release.

## Do not
Add NOT NULL or unique constraints before the data check is clean; delete users; change JWT lifetimes.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-02-identity-and-registry.md. Run task 2.1 (read only) and report the data findings. Then plan 2.2 to 2.9 and ask me about D-3, D-8, D-13 and D-15 before building.
