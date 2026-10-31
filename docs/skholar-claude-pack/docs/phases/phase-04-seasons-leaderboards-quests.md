# Phase 4: Seasons, leaderboards, quests and events

**Release:** R1 (seasonal rankings fully in R2, foundation here) | **SRS:** BE-05, BE-07, BE-20.2, DATA-05, DATA-06, BE-02.4 | **Owner:** Israel | **Size:** XL | **Depends on:** 3

## Goal
Give students something to do and a fair way to see standing: seasons, department/faculty/university boards, and data-driven quests and events, all paying out through the ledger.

## Read first
`docs/DECISIONS.md` (D-5), the Phase 3 design note, SRS BE-05 and BE-07.

## Tasks
- [ ] **4.1 Seasons (BE-20.2).** `Season` (name, type week or term, start, end, state: scheduled / open / closed). Boundaries in Africa/Lagos, stored in UTC. Admin create, schedule, open and close; every action audited.
- [ ] **4.2 Contribution rules (BE-05.2, 05.6).** Published rule config: which activities contribute, weight, per-student cap. `GET /api/v1/scoring-rules` returns it verbatim for both clients.
- [ ] **4.3 Board computation.** Personal boards (lifetime, season, week) scoped to department, faculty and university; department and faculty collective boards from the rule. Indexed queries or a scheduled command first (D-5); only add Celery after load evidence. Past results use the department the student had at the time (Phase 2 history).
- [ ] **4.4 Board endpoint (BE-05.3).** `GET /api/v1/leaderboards/{scope}/{period}` returns, in one response, the student's rank, the entries around them, and the top entries.
- [ ] **4.5 Exclusions (BE-05.5).** Suspended accounts and quarantined awards are excluded from boards until cleared; ledger history stays intact.
- [ ] **4.6 Rollover and archive (BE-05.4).** Closing a season archives immutable `LeaderboardSnapshot` rows, empties week and season boards, leaves lifetime untouched, and emits notification events (consumed in Phase 6).
- [ ] **4.7 Quests (BE-07.1 to 07.3).** `Quest` (type, target, completion rule, reward, availability window, audience) and per-student `QuestProgress` (available, in_progress, completed, claimed, expired). A **validator registry**: one validator per target type (Past Questions session, event attendance now; POI check-in and course progress registered later). Completion is checked on the server against the real record before `award_xp` is called. Non-repeatable quests cannot complete twice.
- [ ] **4.8 Events and endpoints (BE-07.5, 07.6).** `Event` and `EventRegistration` with capacity and attendance. `GET /api/v1/quests/for-me`, `POST /quests/{id}/accept`, `POST /quests/{id}/complete` (idempotent). Group quests (Should) behind a flag.
- [ ] **4.9 Progress data (BE-02.4).** Complete `/me/progress`: level, XP to next, personal rank, department rank, and which activities would improve each.

## Tests required
Rollover empties week and keeps lifetime and archives the old board; rank 47 sees self, neighbours and top 10 in one response; suspended and quarantined excluded; department change does not rewrite past results; client claiming completion without a record gets no reward and is logged; double completion awards once; audience and window filters; capacity limits.

## Acceptance (SRS)
An admin creates a discovery quest in admin and it appears with no deploy; completing it awards XP once. At season rollover the weekly board empties, lifetime is unchanged, last season is still viewable.

## Do not
Hard-code quests, caps or rules; trust a client rank or score; add Redis or Celery without asking.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-04-seasons-leaderboards-quests.md. Plan tasks 4.1 to 4.9, propose the board computation approach (D-5) with expected query cost, and wait for approval.
