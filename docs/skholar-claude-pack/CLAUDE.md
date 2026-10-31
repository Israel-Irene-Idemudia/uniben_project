# CLAUDE.md: Skholar backend (uniben_project)

Django 5.2 + Django REST Framework 3.15 + SimpleJWT backend for Skholar, a student platform at UNIBEN.
We are extending it **in place** for the **Skholar World** update.

- Spec (authoritative): `docs/SRS.md`. If code and SRS disagree, **stop and ask**. Never guess.
- Roadmap: `docs/PHASES.md` (14 phases, 0 to 13). One file per phase in `docs/phases/`.
- Status: `docs/PROGRESS.md`. Open decisions: `docs/DECISIONS.md`. API rules: `docs/API_CONVENTIONS.md`.
- People: **Israel** owns the backend. **Javin** (CTO) owns Flutter, the 3D web world and reviews every merge.
- Modules BE-03 (avatar), BE-13 (presence), BE-17 (analytics), BE-18 (world content) are **Javin's**. Do not build them unless the phase file says to.

## Non-negotiable rules

1. **Branch:** work only on `skholar-world-dev` or short branches off it (`feature/be-04-xp-ledger`). Never commit to or push `main`. Never force-push.
2. **Production is live and migrations run on startup.** The Docker `CMD` and the WSGI hook run `migrate` on every deploy. Any migration that reaches the deployed branch changes the live AWS PostgreSQL database. So migrations must be additive, reversible where practicable, and never edit an existing migration file.
3. **Local database is SQLite.** Leave `DATABASE_URL` unset. Never put a production URL, key or password in any local file. Never read or print `.env`.
4. **Never run** `clear_migrations.py`, `flush_academic_data.py`, `reset_load_cbt.py`, `reset_load_courses.py`, or any other seed, import or flush script against anything but a throwaway local database, and only when Israel asks.
5. **Server authority (D7).** XP, scores, rewards, quest completion and rankings are decided on the server. No endpoint accepts a client-supplied XP, score, balance, price or completion flag.
6. **Legacy routes keep working.** The live Flutter app uses today's `/api/...` routes. Do not rename, remove or change their response shapes. New endpoints go under `/api/v1/`.
7. **No secrets in the repo** (code, tests, docs, fixtures, `.env.example`). Use placeholders only.
8. **Ask before** adding a dependency, adding infrastructure (Redis, Celery, new AWS service), changing `settings.py` behaviour that affects production, or deleting any data or file.

## Working protocol (every task)

1. Read the current phase file, the SRS requirement IDs it cites, and the code it says to inspect.
2. **Plan first.** Reply with a short plan (files to touch, models, endpoints, tests, risks). **Wait for approval** before writing code.
3. Implement one task at a time. Keep each task to one reviewable commit.
4. Run `python manage.py check` and `python manage.py test`. Report exact pass/fail counts. Compare against `docs/BASELINE.md`.
5. Summarise the diff in plain language: what changed, why, any migration, any manual step.
6. Commit on the branch: `type(scope): message` (feat, fix, test, chore, docs, refactor). Cite SRS IDs in the body, e.g. `BE-04.1`.
7. Tick the task in `docs/PROGRESS.md`. Do not push; Israel pushes after review.
8. If a task needs a decision listed in `docs/DECISIONS.md` as BLOCKING, stop and ask.

## Commands (Windows cmd, venv active)

```
venv\Scripts\activate
python manage.py check
python manage.py test                      # whole suite
python manage.py test rewards -v 2         # one app
python manage.py makemigrations --check --dry-run
```

Python **3.11** (matches the production Dockerfile). Tests use SQLite and `FileSystemStorage` automatically (`IS_TESTING` in settings).
SQLite cannot prove PostgreSQL row locking or concurrency. Write the concurrency test anyway, mark it `skipUnless` PostgreSQL, and tell Israel it needs a PostgreSQL run.

## Architecture facts (verify before relying on them)

- Apps: `accounts`, `aiassistant`, `api`, `app_analytics`, `cbt`, `core`, `course`, `events`, `materials`, `news`, `notifications`, `rewards`. Project package: `uniben_portal`.
- Auth: SimpleJWT, access 15 min, refresh 30 days, rotation + blacklist. Custom login view `accounts.views.MyTokenObtainPairView`. Password reset uses `django-rest-passwordreset` with a numeric token.
- Routes today: `/api/...` (news, events, materials, api viewsets), `/api/cbt/`, `/api/core/`, `/api/aiassistant/`, `/api/notifications/`, `/api/analytics/`, `/api/rewards/`, `/api/accounts/`, `/api/token/`, `/api/token/refresh/`, `/api/password_reset/`. Django admin is at `/admin/tps/`.
- `accounts.UserProfile` holds `points` (an integer), `faculty`, `department`, `level` (FKs with `null=True`), `phone`, `network`, `student_id`, `matric_number`. `core.Level` means **academic level (100L, 200L)**, not XP level.
- `rewards.Redemption` records airtime requests. The original redeem view trusted a client `point_cost` (see Phase 0).
- `DEFAULT_PERMISSION_CLASSES` is `IsAuthenticatedOrReadOnly`. There is no global throttling. Root log level is DEBUG. `SECRET_KEY` has an insecure default.
- Hosting moved from Render to AWS. `render.yaml` is likely stale. Deploy facts are in `docs/AUDIT.md` once Phase 0 finishes.
- **Known failing test before we started:** `materials.tests.MaterialAPITests.test_user_materials_list` (ordering). Not ours. Do not mix a fix into feature commits.
- Phase 2 helpers (use, don't rebuild): common.views (V1APIView, PublicV1APIView, V1ListAPIView), common.idempotency.idempotent,
  common.services (log_audit, get_setting, set_setting), common.flags.is_enabled, accounts.permissions.IsNotSuspended,
  accounts.session_revocation.revoke_all_sessions, accounts.account_state (anonymise_user), accounts.lockout.
- Every quest, Past Questions and social view must use permission_classes = [IsAuthenticated, IsNotSuspended].
- Users are never hard-deleted: use anonymise_user (ledger, history and audit rows point at the user).
- Give complete files, not partial edits; one command per line.

## Domain rules

- Product name: **Skholar World**. Assessment feature: **Past Questions**. Never write "CBT" in new student-facing names, routes or models. The legacy `cbt` app keeps its name; record the exception in `docs/DECISIONS.md`.
- XP ledger (BE-04): append-only; no update or delete path in application code; every row has an idempotency key; user FK uses `on_delete=PROTECT` (never CASCADE); balances are computed from the ledger. Replaying an event never double-awards.
- Name XP concepts `XP...` / `LevelConfig`. Never reuse `Level` (that is `core.Level`).
- Content is data (SRS section 3.3, rule 5): quests, news, POIs, questions, rules and caps live in the database and are editable in admin, never hard-coded.
- Season and daily boundaries use **Africa/Lagos** local time. Store timestamps in UTC.
- Every Release 2+ feature ships behind a feature flag, default off.
- Cross-cutting (SRS section 4): authenticated unless marked public; paginated lists; one error shape (API-06); audit trail on every award, score and state change; object-level authorisation on every read and write.

## Definition of Done (per task)

Built to the SRS on a reviewed branch; tests for its rules pass; acceptance criteria demonstrated; config it needs is manageable in admin; docs/contract updated; Javin has reviewed before merge.

## Style

Small focused apps. Business logic in `services.py`, not in views or serializers. Type hints on new code. Tests in `<app>/tests/` (one file per concern). No clever abstractions; readable beats short. Comment the **why** of anything security-sensitive (locks, idempotency, caps, validators).
