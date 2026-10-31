# Phase 8: Badges, friends and communities

**Release:** R2 (behind flags, off until the Release 2 gate) | **SRS:** BE-06, BE-12, DATA-04 (Badge, StudentBadge), DATA-11 | **Owner:** Israel | **Size:** M | **Depends on:** 3, 6

## Goal
Permanent recognition and consent-based social connection. Strangers knock; they do not walk in.

## Tasks
- [ ] **8.1 Badges (BE-06.1, 06.2).** `Badge` (name, icon, criteria as a rule over ledger and activity data, secret or visible) managed in admin. Evaluate automatically when activity is recorded; award once and store the triggering record. Season close settles badge evaluation (hook from Phase 4).
- [ ] **8.2 Profile exposure (BE-06.3, 06.4).** Earned badges and progress toward visible ones on `GET /api/v1/me/badges` and the profile. Badge award emits a notification and a feed-eligible event.
- [ ] **8.3 Friends (BE-12.1).** Requests (send, accept, decline, cancel), removal, blocking. A blocked user cannot request, message or join the blocker's rooms.
- [ ] **8.4 Visibility (BE-12.3).** `VisibilitySetting`: who can find the student and see presence or profile detail; private by default for non-friends. `GET/PATCH /api/v1/me/visibility`.
- [ ] **8.5 Communities (BE-12.2).** Full department and faculty communities from the registry: quests, standings, notices per community.
- [ ] **8.6 Reporting (BE-12.5).** Every social surface routes reports into the Phase 6 moderation queue.

## Tests required
Badge awarded exactly once; secret badge hidden until earned; blocked user cannot find, request or join; block gives the blocker no notification of itself; visibility defaults private for non-friends; no endpoint allows unsolicited DMs (BE-12.4 prohibits them).

## Acceptance (SRS)
Completing the milestone awards the badge once and it shows in both clients. A blocked student cannot find, request or join the blocker's classroom.

## Do not
Add open direct messaging; enable any flag; reveal blocking to the blocked user in a way that notifies them.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-08-badges-friends-communities.md. Plan tasks 8.1 to 8.6. All new features must sit behind feature flags that default off. Wait for approval.
