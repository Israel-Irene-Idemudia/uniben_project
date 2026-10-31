# Skholar World backend: phase plan

**14 phases (0 to 13).** Release 1 = phases 0 to 7. Release 2 = phases 8 to 11. Release 3 = phases 12 and 13.
Release 4 (marketplace transactions, new universities) is out of scope here.

Sizes are relative effort (S, M, L, XL), not calendar time. Each phase is several small, reviewable commits.

| # | Phase | Release | SRS | Size | Depends on |
|---|-------|---------|-----|------|------------|
| 0 | Safety and baseline | R1 | D7, NFR-SEC1, DATA-18 | S | none |
| 1 | Platform foundation | R1 | API-01 to 07, BE-20.1, BE-15.4 | M | 0 |
| 2 | Identity, accounts and registry | R1 | BE-01, BE-02, DATA-01/02 | L | 1 |
| 3 | XP ledger and rewards | R1 | BE-04, DATA-04, API-04 | XL | 1, 2 |
| 4 | Seasons, leaderboards, quests, events | R1 | BE-05, BE-07, BE-20.2 | XL | 3 |
| 5 | Past Questions | R1 | BE-08, DATA-07 | XL | 3, 4 |
| 6 | Feed, notifications, moderation, analytics hooks | R1 | BE-11, 14, 15, 20.3, 17 (hooks) | L | 2, 3, 4, 5 |
| 7 | Release 1 gate | R1 | BE-20.4 to 20.6, NFR-S1, NFR-SEC5, s12, s14 | L | 0 to 6 |
| 8 | Badges, friends, communities | R2 | BE-06, BE-12 | M | 3, 6 |
| 9 | Classrooms | R2 | BE-10, DATA-09 | L | 5, 8 |
| 10 | Courses, RAG and audio | R2 | BE-09, DATA-08 | XL | 3, 4, 6 |
| 11 | Release 2 gate | R2 | s12, s14 | M | 8 to 10 |
| 12 | Business discovery and live location | R3 | BE-19.1/19.2, BE-16, BE-13 (support) | L | 8, 11 |
| 13 | Release 3 gate | R3 | BE-16.6, s12, s14 | M | 12 |

## Dependency picture

```
0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7   (Release 1 ships when 7 is signed)
              3 -> 8 -> 9               (flagged, off)
         3,4,6 -> 10                    (flagged, off)
                 8,9,10 -> 11
                      8,11 -> 12 -> 13
```

## Rules for ordering

- **Phase 3 (ledger) is the keystone.** Quests, leaderboards, Past Questions, badges and courses all write XP through it. Nothing awards XP any other way.
- Release 2 and 3 features **may be built early, but only behind feature flags that stay off** until their gate (phases 11 and 13) is signed. Location sharing stays disabled until its privacy sign-off.
- A phase is done only when its tasks are ticked in `PROGRESS.md`, its tests pass, and Javin has reviewed.
- Javin's modules (BE-03, BE-13, BE-17, BE-18) are not phases here. The backend side only supplies the hooks each phase lists.

## How to run a phase with Claude Code

1. Open a **fresh** Claude Code session in the project folder (short sessions use less of your allowance).
2. Paste the **Start prompt** from the bottom of the phase file.
3. Review its plan, answer any BLOCKING decisions from `DECISIONS.md`, approve.
4. After each task: read the diff, run the tests yourself, then push after review.
5. Merge the phase to `skholar-world-dev` only after Javin reviews. Never to `main` until a release gate is signed.

## Gate meaning (SRS section 12)

Every Must requirement passes on staging and a production smoke test; performance and accessibility checks pass; regression passes; backup taken and restore demonstrated; rollback rehearsed; real-student beta reviewed; costs within the agreed ceiling.
