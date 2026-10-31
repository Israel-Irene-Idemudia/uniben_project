# Proposed Git checkpoint commits

All six groups have been prepared in separate temporary Git indexes for pre-commit review. At the approval boundary, only group 1 documentation is staged in the real index; groups 2-6 remain in their separate temporary indexes and patches. No commits have been created. Files below are explicit allowlists; no directory-wide staging or generated media is included. See the pre-commit review in FINAL_SAFETY_REVIEW.md for intermediate validation results.

## 1. `docs(project): reconcile specifications and record preservation review`

Whole files:

```text
docs/FINAL_SAFETY_REVIEW.md
docs/GIT_CHECKPOINT_MANIFEST.json
docs/GIT_CHECKPOINT_PLAN.md
docs/IMPLEMENTATION_CHECKPOINT_HASHES.json
docs/MEDIA_SAFETY_INVENTORY.json
docs/PRESERVATION_REVIEW.md
docs/SKHOLAR_HANDOFF.md
docs/design/xp-ledger.md
docs/skholar-claude-pack/CLAUDE.md
docs/skholar-claude-pack/README.md
docs/skholar-claude-pack/docs/API_CONVENTIONS.md
docs/skholar-claude-pack/docs/DECISIONS.md
docs/skholar-claude-pack/docs/PHASES.md
docs/skholar-claude-pack/docs/PROGRESS.md
docs/skholar-claude-pack/docs/SRS.md
docs/skholar-claude-pack/docs/phases/phase-00-safety-and-baseline.md
docs/skholar-claude-pack/docs/phases/phase-01-platform-foundation.md
docs/skholar-claude-pack/docs/phases/phase-02-identity-and-registry.md
docs/skholar-claude-pack/docs/phases/phase-03-xp-ledger-and-rewards.md
docs/skholar-claude-pack/docs/phases/phase-04-seasons-leaderboards-quests.md
docs/skholar-claude-pack/docs/phases/phase-05-past-questions.md
docs/skholar-claude-pack/docs/phases/phase-06-feed-notifications-moderation.md
docs/skholar-claude-pack/docs/phases/phase-07-release-1-gate.md
docs/skholar-claude-pack/docs/phases/phase-08-badges-friends-communities.md
docs/skholar-claude-pack/docs/phases/phase-09-classrooms.md
docs/skholar-claude-pack/docs/phases/phase-10-courses-rag-audio.md
docs/skholar-claude-pack/docs/phases/phase-11-release-2-gate.md
docs/skholar-claude-pack/docs/phases/phase-12-business-and-location.md
docs/skholar-claude-pack/docs/phases/phase-13-release-3-gate.md
```

## 2. `feat(xp): preserve ledger and server-priced rewards`

Whole files:

```text
accounts/admin.py
accounts/tests/test_v1_me.py
accounts/tests/test_v1_me_xp.py
materials/views.py
rewards/admin.py
rewards/migrations/0002_reward_catalog.py
rewards/migrations/0003_seed_reward_catalog.py
rewards/models.py
rewards/services.py
rewards/test_redeem_validation.py
rewards/tests.py
rewards/v1_urls.py
rewards/v1_views.py
rewards/views.py
uniben_portal/urls.py
xp/__init__.py
xp/admin_base.py
xp/apps.py
xp/management/__init__.py
xp/management/commands/__init__.py
xp/management/commands/reconcile_points.py
xp/migrations/0001_xp_ledger.py
xp/migrations/0002_seed_rules_and_levels.py
xp/migrations/0003_opening_balances.py
xp/migrations/__init__.py
xp/serializers.py
xp/services.py
xp/tests/__init__.py
xp/tests/helpers.py
xp/tests/test_admin.py
xp/tests/test_api.py
xp/tests/test_migrations.py
xp/tests/test_models.py
xp/tests/test_services.py
xp/urls.py
xp/views.py
```

Selected content only:

- `accounts/v1_profile.py`: XP service import, public XP level/title, and ledger-backed progress_payload only. Leave university-related changes for group 3.
- `xp/models.py`: XPLedgerEntryQuerySet, XPLedgerEntry, XPAdjustment, XPRule, LevelConfig, and required imports. Leave XPQuarantineQuerySet and XPQuarantine for group 6. Current season-window explanatory docstring may stay as documentation; it imports no future app.
- `xp/admin.py`: Ledger, adjustment, rule and level forms/admin, with imports matching those classes. Leave quarantine imports, XPQuarantineForm and XPQuarantineAdmin for group 6.
- `uniben_portal/settings.py`: Comma required after CommonConfig and xp.apps.XpConfig registration only.

## 3. `feat(core): preserve minimum multi-university foundation`

Whole files:

```text
core/admin.py
core/migrations/0006_university_faculty_university.py
core/migrations/0007_seed_uniben.py
core/models.py
core/tests/test_university.py
core/v1_serializers.py
core/v1_urls.py
core/v1_views.py
```

Selected content only:

- `accounts/v1_profile.py`: University-aware _PROFILE_RELATED and profile_for, university_of helper, university reference in public_profile. Retain group 2 XP changes.

## 4. `feat(seasons): preserve audited season lifecycle`

Whole files:

```text
seasons/__init__.py
seasons/admin.py
seasons/apps.py
seasons/migrations/0001_initial.py
seasons/migrations/__init__.py
seasons/models.py
seasons/serializers.py
seasons/services.py
seasons/tests/__init__.py
seasons/tests/test_admin.py
seasons/tests/test_api.py
seasons/tests/test_services.py
seasons/v1_urls.py
seasons/views.py
```

Selected content only:

- `uniben_portal/settings.py`: seasons.apps.SeasonsConfig registration only.
- `common/v1_urls.py`: seasons.v1_urls include only.

## 5. `feat(leaderboards): preserve contribution rules and personal boards`

Whole files:

```text
leaderboards/__init__.py
leaderboards/admin.py
leaderboards/apps.py
leaderboards/management/__init__.py
leaderboards/management/commands/__init__.py
leaderboards/management/commands/explain_leaderboard.py
leaderboards/migrations/0001_initial.py
leaderboards/migrations/__init__.py
leaderboards/models.py
leaderboards/serializers.py
leaderboards/services.py
leaderboards/tests/__init__.py
leaderboards/tests/board_helpers.py
leaderboards/tests/test_admin.py
leaderboards/tests/test_api.py
leaderboards/tests/test_board_api.py
leaderboards/tests/test_board_endpoint.py
leaderboards/tests/test_boards.py
leaderboards/tests/test_explain_command.py
leaderboards/tests/test_services.py
leaderboards/v1_urls.py
leaderboards/views.py
```

Selected content only:

- `uniben_portal/settings.py`: leaderboards.apps.LeaderboardsConfig registration only.
- `common/v1_urls.py`: leaderboards.v1_urls include only.
- `leaderboards/boards.py`: Personal board computation, top/page/me/around_me, scoring/window/isolation and suspended/deleted exclusions. Leave quarantine docstring bullet, XPQuarantine import, quarantine table lookup, and quarantined-award NOT EXISTS block (including params.extend) for group 6.

## 6. `feat(leaderboards): preserve quarantined award exclusions`

Whole files:

```text
leaderboards/tests/test_quarantine_exclusion.py
xp/migrations/0004_xp_quarantine.py
xp/quarantine.py
xp/tests/test_quarantine.py
```

Selected content only:

- `xp/models.py`: XPQuarantineQuerySet and XPQuarantine, preserving existing ledger model contents.
- `xp/admin.py`: XPQuarantine and quarantine-service imports, XPQuarantineForm and XPQuarantineAdmin.
- `leaderboards/boards.py`: Quarantine explanatory bullet, XPQuarantine import, quarantine table lookup, EXCLUDING_STATES and NOT EXISTS predicate with its parameters.

## Excluded from all six commits

These files remain in place and unstaged.

```text
avatar_usage.txt
docs/skholar-claude-pack/.claude/settings.json
git_log.txt
git_status.txt
kholar-world-dev
materials/test_doc_LwpacbU.pdf
materials/test_doc_UGAex6l.pdf
materials/test_doc_fOtK4tb.pdf
migrations_list.txt
phase2_data_check.py
points_grep.txt
points_usage.txt
tree.txt
```

All ignored media, .env files other than the already tracked template, SQLite databases, virtual environments, caches and local logs remain excluded. All 24 untracked/ignored test PDFs are exact pdf_content placeholders. Existing tracked media is not added, removed, or changed by these groups.

## Dependency and approval gates

Group 3 depends on group 2 profile imports. Group 5 depends on the XP, university and seasons groups. Group 6 completes quarantine across XP and board SQL. No standalone quarantine-dependent file may be staged early. A normal file-level git add on the six shared paths would break this partition.

If keeping six independently valid commits requires reconstructing application files, request approval for one combined implementation preservation commit (groups 2-6) plus the documentation commit. Keep the tested final source unchanged. The original 439-test validation passed with 2 skips. Cumulative intermediate snapshots have now been tested: checks and migration consistency pass throughout; the known materials-ordering test is the sole failure in groups 2, 4, 5 and 6, and passes when rerun alone with configured password hashing. No application fix was mixed into these commits.

Execution of the six commits requires final staged-summary approval. No push is authorized. Before push, resolve the deployment integration gate and request Israel's final approval. Phase 4.6 (Leaderboard Snapshots) starts after the Git checkpoint.
