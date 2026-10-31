# Preservation review ? 31 Oct 2026

## Scope and authority

Read-only inspection was followed by Israel's approval to reconcile documentation and validate. No staging, commit, push, deletion, reset, application-code change, or deployment is authorized by that approval.

Branch: `skholar-world-dev`, HEAD `f806bd6`. Initial inventory: 16 modified tracked files and 110 untracked files; index empty. HEAD matched the locally recorded upstream; GitHub was not contacted. Historical handoff claims about unpushed Phase 2 commits are superseded by this local observation, not by a live remote check.

## Preserve and exclude

Preserve XP/rewards implementation and tests, university foundation and tests, seasons, contribution configuration, personal boards and exclusions, all ten new migrations, and project specifications. Review `phase2_data_check.py` separately as a counts-only Phase 2 diagnostic; do not execute it during preservation. Review the nested `.claude/settings.json` separately as tooling configuration.

Exclude scratch outputs `avatar_usage.txt`, `git_log.txt`, `git_status.txt`, `migrations_list.txt`, `points_grep.txt`, `points_usage.txt`, `tree.txt`, and `kholar-world-dev` (Git help output). Exclude the three new `materials/test_doc_*.pdf` artifacts. Exclusion means leaving files in place and unstaged, not deleting them.

## Sensitive content and existing history

`.env` and `db.sqlite3` are ignored and untracked; neither was opened. Pattern scanning of pending text files found no obvious credentials; flagged passwords were test fixtures. This is a heuristic scan, not a full privacy or history audit. Do not use `git add .`.

Sixty paths under `media/` are already tracked, along with material PDFs elsewhere. Ignore rules do not protect already tracked content. Their privacy and publication status must be resolved before push; no removal or history rewrite is authorized. A metadata review of initial_data.json (1,395 registry records) and cbt_questions.json (13,843 assessment records) found no obvious personal/credential field names; this is not a content or copyright clearance. A broader scan of 375 tracked text files found only placeholder credential URLs and test-password matches. Git history and binary files remain outside that scan.

## Documentation reconciliation

The old handoff is retained as historical context with a superseding current-status notice. D-1, D-2 and D-12 now describe existing choices recorded in the design note, without inventing new approvals. D-17 supersedes the original ledger-season-FK plan. Progress ticks are historical implementation markers, not evidence that the review and commit gates passed. `/me/progress` ranks remain null until task 4.9.

## Validation

Final result: **439 tests run in 38.593 seconds; 437 passed, 2 skipped, 0 failures, 0 errors**. System check passed and migration consistency reported no changes. Normal logging was enabled. This is SQLite behavioral validation with process-only overrides, not production performance or PostgreSQL validation. All 91 pending Python files parsed successfully.

Validation uses Python from the existing venv, no `.env` loader, dummy service credentials, in-memory SQLite, temporary media storage, and local-memory email. The corrected harness preserves the configured MEDIA_ROOT while setting the storage backend location to a temporary directory, and keeps the configured password hashers available alongside the fast test default. Settings overrides exist only in the validation process. Python runs with `-B`. The first full run with default password hashing was stopped because of slow progress; the restarted behavioral run uses Django MD5PasswordHasher only in process. This does not validate production password-hashing cost or performance. Temporary test media directories are retained; no cleanup deletion was performed.

- System check: passed with isolated configuration.
- Migration consistency (`makemigrations --check --dry-run`): no changes detected.
- First completed isolated run: 439 tests, 1 failure, 1 error, 2 skipped. Both problems were validation-harness effects: missing PBKDF2-SHA1 support and overriding MEDIA_ROOT in a test that asserts its configured path. A second run corrected those issues but failed four logging assertions because the harness disabled logging globally (439 tests, 4 failures, 2 skipped). Normal logging was restored for the successful final run. These interim results are harness failures, not claimed application regressions.
- Initial isolated check exposed the empty CORS default; supplying `http://localhost` in the process environment resolved it without source changes.
- `git diff --check`: passed at initial inspection; line-ending warnings exist.

## Proposed commit sequence

Use explicit paths and selective staging for shared files; do not reconstruct lost intermediate versions or claim individual historical task commits. Each commit must include its imports, app registration, routing and migration dependencies and be validated independently.

1. Reconciled project documentation and specifications.
2. XP ledger, reward catalogue/redemption, material awards and profile XP integration (Phase 3).
3. Multi-university foundation and registry/profile integration.
4. Seasons (4.1).
5. Contribution configuration and personal boards through 4.4.
6. Quarantine record/admin and board exclusions (4.5).

Current files combine Phase 3/4 changes, especially settings, profiles, routing, XP models and admin. If a clean split needs application-code edits or cannot produce independently valid commits, propose a combined preservation commit before staging. Test the actual staged result, not only the final working tree. Obtain explicit approval before commits and again before push.

## Outstanding release gates

Production Phase 2 registry counts and backfill readiness; reward-price verification; opening-balance rehearsal and reconciliation on an isolated restored copy; Javin review; D-18 collective-board choices; D-10 deployment/branch facts; PostgreSQL concurrency tests and D-21 query plans. No production database or migration command was used. Confirm whether pushing the development branch triggers deployment before any push. Git preservation is not release approval.

## Final safety checks

See [final safety review](FINAL_SAFETY_REVIEW.md) and [exact commit plan](GIT_CHECKPOINT_PLAN.md). Live remote development HEAD was confirmed as f806bd6. Media is unchanged; existing tutorial contacts and incomplete scanned-page clearance are recorded. Push is not cleared while active hosting integration/branch settings remain unknown: render.yaml enables autoDeploy and deployment entrypoints run migrations. No commits, staging, push, deployment or application edits were performed.
