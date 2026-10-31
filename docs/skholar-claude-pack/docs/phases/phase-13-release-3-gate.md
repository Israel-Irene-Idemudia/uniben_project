# Phase 13: Release 3 gate

**Release:** R3 | **SRS:** BE-16.6, NFR-SEC3, NFR-SEC5, section 12, section 14, Appendix C | **Owner:** Israel and Javin | **Size:** M | **Depends on:** 12

## Goal
Prove Release 3 is safe, with location sharing treated as the highest-risk feature.

## Tasks
- [ ] **13.1 Data-protection review (BE-16.6).** Complete and sign the documented review against the Nigeria Data Protection Act 2023 and update the privacy notice in plain language (what is collected, why, visibility defaults, retention).
- [ ] **13.2 Location security review.** Threat checklist: stalking and over-sharing paths, expiry bypass, spoofing, audience leaks, logging of coordinates, retention.
- [ ] **13.3 Abuse tests.** Attempts to read another student's location, extend a session, bypass audience, or obtain history must all fail and be logged.
- [ ] **13.4 Business moderation drill.** Takedown, verification and report handling end to end; confirm no payment path exists anywhere.
- [ ] **13.5 Migration, backup, restore and rollback** rehearsal for Release 3 data changes on staging.
- [ ] **13.6 Load and failure tests.** Presence down means learning still works; location endpoints under cohort load.
- [ ] **13.7 Regression** of Releases 1 and 2 and the existing tools.
- [ ] **13.8 Sign-off.** Appendix C: BE-16.6 privacy sign-off, then flag rollout plan (smallest cohort first, switch-off tested).

## Do not
Enable the location flag without the signed review; merge to `main` before both developers sign.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-13-release-3-gate.md. Draft the review pack, test scripts and checklists for 13.1 to 13.8, one at a time, and wait for my approval after each.
