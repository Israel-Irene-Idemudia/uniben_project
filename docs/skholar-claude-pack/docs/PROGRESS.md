# Progress tracker

Tick a task only when its commit exists on `skholar-world-dev`, tests pass, and the diff is reviewed.
Sign-off lines are for Israel (owner) and Javin (reviewer).

## Preservation review (31 Oct 2026)

Phase 3, the minimum university foundation, and Phases 4.1-4.5 have implementation and tests in the working tree, not committed at this inspection. Existing ticks below are historical implementation markers, not proof of the commit/review rule above. No new completion ticks are added. Collective boards remain blocked on D-18; snapshots remain task 4.6. See [preservation review](../../PRESERVATION_REVIEW.md) for validation and remaining gates.

## Release 1
- [x] **Phase 0** Safety and baseline (0.1 to 0.6) | Israel [accepted] Javin [accepted]
- [x] **Phase 1** Platform foundation (1.1 to 1.9) | Israel [accepted] Javin [ ]
      Health routes were missing from the pushed commit; fixed in Phase 2.
- [ ] **Phase 2** Identity, accounts and registry | Israel [done in code, 29 Oct] Javin [ ]
      - [ ] 2.1 Registry data check on PRODUCTION (read only): NOT YET RUN. Local DB was empty. Blocks deploy of 2.3.
      - [x] F9 password-reset hardening (extra task, found in review)
      - [x] 2.2 registry code/is_active, no-delete admin, public v1 faculties and departments
      - [x] 2.3 StudentDepartmentHistory + backfill + sync signal
      - [x] 2.4 v1 /me and /me/progress
      - [x] 2.5 department change (once per semester, admin approval)
      - [x] 2.6 world hand-off token
      - [x] 2.7 session revocation on password change and admin action
      - [x] 2.8 login lockout and auth log
      - [x] 2.9 account states, anonymising deletion, data export
- [ ] **Phase 3** XP ledger and rewards (3.1 to 3.10) | Israel [ ] Javin [ ]
      - [x] /me and /me/progress read XP, level and balance from the ledger (30 Oct)
- [ ] **Phase 4** Seasons, leaderboards, quests, events (4.1 to 4.9) | Israel [ ] Javin [ ]
      - [x] D-16 minimum: core.University, Faculty.university, UNIBEN seed, /api/v1/universities (core 0006, 0007)
      - [x] 4.1 Seasons: model, audited admin lifecycle, GET /api/v1/seasons/current (seasons 0001)
      - [ ] 4.2 Contribution rules: built in code, not committed. ContributionRuleSet/Item, audited admin, activation permission, GET /api/v1/scoring-rules (leaderboards 0001). No rule values seeded (D-18 open).
      - [ ] 4.3 Personal boards: built in code, not committed (30 Oct). leaderboards/boards.py, GET /api/v1/leaderboards/{scope}/{period}, explain_leaderboard command. No migration. Collective boards wait on D-18. Open D-19 items resolved (opening balances excluded; 1, 1, 3 ranking). PostgreSQL plans deferred to staging (D-21, mandatory pre-production).
      - [ ] 4.4 Board endpoint (BE-05.3): built in code, not committed (30 Oct). Additive `top` list (default 10, 0..100, independent of offset) on GET /api/v1/leaderboards/{scope}/{period}; top, page, me and neighbours from one board query (D-20). `--top` on explain_leaderboard. No migration, no index. Tests: leaderboards/tests/test_board_endpoint.py (rank-47 acceptance, paging, one-query check, isolation) + top cases in test_boards.py. Javin to review the contract.
      - [ ] 4.5 Exclusions (BE-05.5): built in code, not committed (30 Oct). Minimum quarantine record per D-22: `xp.XPQuarantine` (xp 0004, one additive CreateModel, not applied anywhere shared), `xp.quarantine.quarantine_award` (permission `xp.quarantine_xp_award`, mandatory reason, AuditLog `xp.quarantine`, idempotent, award rows only), admin add + read-only view, no API endpoint. Boards skip quarantined awards per ledger row (one NOT EXISTS in the existing single board query); suspended/deleted exclusion unchanged. Ledger, balance and level unchanged. Tests: leaderboards/tests/test_quarantine_exclusion.py, xp/tests/test_quarantine.py. Review workflow, clearing, detectors and appeals stay in 5.8 / 6.7.
      - [ ] 4.6 to 4.9
- [ ] **Phase 5** Past Questions (5.1 to 5.10) | Israel [ ] Javin [ ]
- [ ] **Phase 6** Feed, notifications, moderation, analytics hooks (6.1 to 6.9) | Israel [ ] Javin [ ]
- [ ] **Phase 7** Release 1 gate (7.1 to 7.10) | Israel [ ] Javin [ ] (both initial Appendix C)

## Release 2 (built behind flags, kept off)
- [ ] **Phase 8** Badges, friends, communities | Israel [ ] Javin [ ]
- [ ] **Phase 9** Classrooms | Israel [ ] Javin [ ]
- [ ] **Phase 10** Courses, RAG and audio | Israel [ ] Javin [ ]
- [ ] **Phase 11** Release 2 gate | Israel [ ] Javin [ ]

## Release 3 (built behind flags, kept off)
- [ ] **Phase 12** Business discovery and live location | Israel [ ] Javin [ ]
- [ ] **Phase 13** Release 3 gate (includes BE-16.6 privacy sign-off) | Israel [ ] Javin [ ]

## Notes and blockers
27 Oct 2026: Phase 0 done on skholar-world-dev (5 commits). Open: MEDIA_ROOT fix not deployed, live admin password reset, F3 and F4 pending Javin.
28 Oct 2026: Phase 1 complete in code (common app: v1 base, error shape, pagination, idempotency, throttling, flags, settings, audit, health). 4 additive migrations.
29 Oct 2026: Phase 2 complete in code (accounts 0010 to 0015, core 0005, all additive; 0012 is a data backfill). 231 tests OK, 2 skipped. 10 local commits, not reviewed by Javin, not deployed.
  Before deploy: run 2.1 on AWS; Javin reviews; deploy Phase 2 as one batch. Flutter-facing changes Javin must check: 429 on login and password reset, reset code now lasts 15 minutes, password change signs out other devices, account deletion now anonymises, new /api/v1 routes.
31 Oct 2026 preservation validation: 439 tests run, 437 passed, 2 skipped, no failures/errors; system check passed; migration consistency reported no changes. Isolated SQLite, temporary upload storage, dummy service configuration, fast test password hasher plus configured hashers; no .env loader. Details and interim harness corrections: docs/PRESERVATION_REVIEW.md. No staging, commit, push or deployment performed.
