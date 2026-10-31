# Phase 7: Release 1 gate

**Release:** R1 | **SRS:** BE-20.4 to 20.6, NFR-S1, NFR-R3, NFR-SEC1 to 5, NFR-M3, section 12, section 14, Appendix C | **Owner:** Israel and Javin jointly | **Size:** L | **Depends on:** 0 to 6

## Goal
Prove Release 1 is safe to launch. Claude Code writes the scripts, tests and documents; **people run them on staging** and sign.

## Read first
`docs/DECISIONS.md` (D-6, D-10), SRS sections 12, 14 and Appendix C.

## Tasks
- [ ] **7.1 Contract tests.** One automated test per row of the endpoint catalogue that Release 1 ships, checking method, auth, response shape and error shape.
- [ ] **7.2 Abuse tests (section 14.1).** Scripted attempts that must fail and be logged: XP farming, replaying completions, reading Past Questions answers early, accessing another student's objects (IDOR), client-supplied XP or price.
- [ ] **7.3 Staging parity.** Document the staging environment (separate database and bucket) and the steps to refresh it with production-like data volume (D-10).
- [ ] **7.4 Migration rehearsal (BE-20.6).** Checklist and script to run every Release 1 migration on a copy of production data; row counts before and after; the points reconciliation report (Phase 3) attached.
- [ ] **7.5 Backup and restore (BE-20.4).** Backup schedule, pre-deploy backup step, and a written, tested restore procedure. The restore must be **demonstrated** on staging.
- [ ] **7.6 Rollback rehearsal (NFR-R3).** Written rollback procedure for a bad deploy including migrations.
- [ ] **7.7 Monitoring (BE-20.5).** Health and readiness wired to alerts; error monitoring (Sentry or equivalent) configured with secrets from the environment only.
- [ ] **7.8 Load test (NFR-S1, NFR-P4).** Test plan and script (for example k6 or Locust) sized to the cohort in D-6, modelling the exam-season Past Questions peak; target p95 under 500 ms for ordinary reads.
- [ ] **7.9 Security and privacy review (NFR-SEC5).** Checklist covering auth, awards, competitive scoring, admin; privacy notice reviewed against the Nigeria Data Protection Act 2023; secrets scan; dependency update pass; production settings (`DEBUG`, `SECRET_KEY`, log level, default permissions).
- [ ] **7.10 Runbooks and cost (NFR-M3, NFR-C1).** Runbooks: deploy and rollback, season close, backup restore, moderation escalation, incident communication. Per-user cost estimate for each variable-cost feature.

## Gate checklist (all true before launch)
Every Must passes on staging and in a production smoke test; golden path works in both clients (register, onboard, avatar, enter world, quest, Past Questions, XP and rank visible); regression of existing Skholar tools passes; backup taken and restore demonstrated; rollback rehearsed; real-student beta reviewed; costs within the agreed ceiling; Israel and Javin initial Appendix C.

## Do not
Merge to `main` or enable production flags yourself. Claude Code prepares; Israel and Javin decide.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-07-release-1-gate.md. Produce the scripts and documents for tasks 7.1 to 7.10 one at a time, starting with 7.1 and 7.2, and wait for my approval after each.
