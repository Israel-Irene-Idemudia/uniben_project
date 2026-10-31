# Phase 11: Release 2 gate

**Release:** R2 | **SRS:** section 12, section 14, NFR-C2, NFR-R3 | **Owner:** Israel and Javin | **Size:** M | **Depends on:** 8, 9, 10

## Goal
Prove Release 2 is ready to switch on, flag by flag.

## Tasks
- [ ] **11.1 Contract and abuse tests** for every Release 2 endpoint (rooms, friends, badges, courses, audio).
- [ ] **11.2 Authorisation sweep.** Automated checks that no student can read or change another student's room, friendship, progress or submission.
- [ ] **11.3 Cost review.** Real measured AI and speech cost per active learner against the agreed ceiling; audio cache hit rate reported (BE-09.5).
- [ ] **11.4 Migration rehearsal, backup, restore and rollback** for the Release 2 data changes, on staging.
- [ ] **11.5 Load check** of audio streaming and room endpoints against the cohort size.
- [ ] **11.6 Regression** of everything from Release 1 and the existing Skholar tools.
- [ ] **11.7 Flag rollout plan.** Per cohort or department; who enables each flag and how to switch it off.
- [ ] **11.8 Beta review** with real students (gamers and non-gamers) and sign-off in Appendix C.

## Do not
Enable flags in production yourself; merge to `main` before both developers sign.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-11-release-2-gate.md. Draft the checklists, scripts and tests for 11.1 to 11.8, one at a time, and wait for my approval after each.
