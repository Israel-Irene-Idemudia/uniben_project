# SKHOLAR HANDOFF: read this first in every chat

Last reviewed: 31 Oct 2026.

Current handoff: Phase 3, the minimum multi-university foundation, and Phases 4.1-4.5 are present as uncommitted implementation. Codex has approval to reconcile documentation and validate, but not to stage, commit, push, delete, reset, or change application code. Preserve the completed work on skholar-world-dev after explicit approval, then continue Phase 4.6 (Leaderboard Snapshots). See [preservation review](PRESERVATION_REVIEW.md).

The sections below preserve the 29 Oct historical handoff. Their phase status, remote status, and next-step instructions are superseded by this notice and the preservation review; they are not current execution instructions.

## 1. Who and what

- **Israel** owns the Skholar backend. **Javin** (Oreoluwa Ifedinma Chiazor, CTO) owns Flutter, the Three.js 3D world, and reviews every merge.
- Project: **Skholar World** update (SRS TPS-SKH-SRS-001 v1.0, 15 Oct 2026). Launches at UNIBEN first.
- Backend repo: `uniben_project` (Django 5.2, DRF, SimpleJWT). Python 3.11. Hosting is on AWS (the old Render setup is stale).
- Branch: **`skholar-world-dev`**. `main` is never touched until a release gate is signed.

## 2. How we are working

- Israel is on the **free Claude plan** with no Claude Code, so Claude cannot run code, tests or git. Israel runs everything and pastes results back.
- Source of truth for rules: `CLAUDE.md`. Requirements: `docs/SRS.md`. If code and SRS disagree, stop and ask.
- Every task: short plan first, wait for approval, then **complete files** (not partial edits). Israel pastes them in, runs `python manage.py check` and the tests, pastes the output back, and commits.
- Windows cmd, venv active. Give **one command per line** (a `git add` once got glued onto a test command).
- One fresh chat per phase. Claude only sees the files in the Project plus what Israel pastes, so Claude must say which files it still needs rather than guessing.
- Israel never pastes `.env` contents, real keys, passwords or production URLs. Placeholders only.
- Test runs are slow on Israel's laptop (every login hashes a password). Use `python manage.py test <app>` while working; run the full suite before committing and before pushing.

## 3. Where we stopped

| Phase | Status |
|-------|--------|
| 0 Safety and baseline | Done, reviewed |
| 1 Platform foundation | Done, pushed. Health routes were missing from the pushed commit and were fixed in Phase 2 |
| 2 Identity, accounts, registry | **Done in code**, 10 local commits, 231 tests OK, **not pushed to review, not deployed** |
| 3 to 13 | Not started |

Phase 2 commits on `skholar-world-dev` (oldest first): `c5b2424` accounts `__init__` and tests folder; `e8cde0c` F9 password-reset hardening; health routes fix; `1eb635e` 2.2 registry; `1578191` 2.3 department history; `96e0abf` 2.4 `/me`; `2299bc9` + `db49620` 2.5 department change; `8933f31` 2.6 hand-off + 2.7 session revocation; `f806bd6` 2.8 lockout + 2.9 account states.

Phase 2 still needs before sign-off:
1. **Task 2.1 production data check** (`phase2_data_check.py`, run on AWS, paste printed counts only). Never run against production from a laptop. The 2.3 backfill must not reach production before this.
2. **Javin's review** of everything above.
3. **D-3 semester dates** for 2026/27 (a fallback of 180 days is in use).

Deploy as ONE batch, after those three: 2.3 history rows block hard user deletes, and 2.9 replaced both hard-delete paths with anonymising. The new migrations are accounts 0010 to 0015 and core 0005. All are additive; 0012 is a data backfill.

## 4. Next step

**Phase 3, task 3.1.** Israel pastes: `git status`, `git log --oneline -5`, the phase 3 file, and the files its "Read first" lists.
Phase 3 is BLOCKED until Israel answers **D-1** (reward prices) and **D-2** (points vs XP), and proposes **D-12** (XP rules and level curve).

## 5. What is in the Project

Knowledge files: this file, `SRS.md`, `PHASES.md`, `PROGRESS.md`, `DECISIONS.md`, `API_CONVENTIONS.md`, `AUDIT.md`, `BASELINE.md`, the current phase file (`phase-03-...md`), and the map files: `urls.py` (root), `settings.py` (secrets REDACTED), `tree.txt`, `accounts_models.py`, `core_models.py`, `reward_models.py`, `common_models.py`, `common_services.py`, `common_views.py`.
Add each next phase file only when you reach it. Per task, paste only the files that task touches, plus test output.
**Never upload or paste:** `.env`, production DB URLs, AWS keys, `SECRET_KEY` values, user data exports.

## 6. Decisions

- **BLOCKING for Phase 3:** D-1, D-2. D-12 is needed in Phase 3.
- **BLOCKING for Phase 7:** D-10 (AWS deploy facts).
- Answers so far are recorded with dates in `DECISIONS.md`.

## 7. Known facts to keep in mind

- Production is live and migrations run on startup. Any migration that reaches the deployed branch changes the live PostgreSQL database. Migrations must be additive.
- Local DB is SQLite. It cannot prove PostgreSQL locking, so concurrency tests are `skipUnless` PostgreSQL (2 are skipped).
- `materials.tests.MaterialAPITests.test_user_materials_list` is flaky (ordering): sometimes passes, not ours.
- `core.Level` means academic level (100L). XP concepts must be named `XP...` or `LevelConfig`.
- New student-facing names say "Past Questions", never "CBT". The legacy `cbt` app keeps its name (D-14). Known leftover: the welcome email in `accounts/signals.py` still says "CBT exams".
- Legacy `/api/...` routes keep working. New endpoints go under `/api/v1/`.
- Javin owns BE-03 (avatar), BE-13 (presence), BE-17 (analytics), BE-18 (world content).

Helpers that exist now (use them, do not rebuild):
- `common.views`: `V1APIView` (authenticated), `PublicV1APIView`, `V1ListAPIView` (cursor), `V1AdminListAPIView`. Every v1 view must use these (a test enforces it).
- `common.idempotency.idempotent` (decorator, needs an `Idempotency-Key` header), `common.services`: `log_audit`, `get_setting`, `set_setting`; `common.flags.is_enabled`; `common.throttling`: `V1DefaultThrottle`, `V1AuthThrottle`, `V1CompetitiveThrottle`; `common.exceptions.ConflictError`.
- `accounts.permissions.IsNotSuspended`: **Phases 4, 5 and 8 must put it on every quest, Past Questions and social view** (after `IsAuthenticated`).
- `accounts.session_revocation.revoke_all_sessions`, `accounts.account_state` (`get_account_state`, `set_account_state`, `anonymise_user`), `accounts.services.change_department`, `accounts.lockout`.
- A password change signs the student out everywhere (signal in `accounts/signals.py`). Access tokens (15 min) cannot be recalled.

Points today (for Phase 3): `UserProfile.points` is a plain integer. Writers: the redeem endpoint (subtracts, price still sent by the client until D-1) and `materials/views.py:120` (+10 on verification, not idempotent). `anonymise_user` leaves points untouched. `GET /api/v1/me/progress` returns `ledger_ready: false` and null XP fields; Phase 3 fills the ledger fields, Phase 4 the ranks.

## 8. After each task, Israel updates

1. Tick the task in `PROGRESS.md` (only when committed, tests pass, diff reviewed).
2. Add a dated line under "Where we stopped" in this file.
3. Re-upload any map file that changed (`models.py` files, `urls.py`, tree).
4. Push to `skholar-world-dev` after review. Merge only after Javin reviews.