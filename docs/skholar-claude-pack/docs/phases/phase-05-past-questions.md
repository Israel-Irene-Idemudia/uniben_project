# Phase 5: Past Questions

**Release:** R1 | **SRS:** BE-08.1 to 08.9, DATA-07, D2, BE-15.5 (anomaly hook) | **Owner:** Israel | **Size:** XL | **Depends on:** 3, 4

## Goal
Formalise the existing question feature as **Past Questions**: practice mode, timed competitive mode scored on the server, tournaments, anti-cheating, and no loss of existing questions or attempt history.

## Read first
`docs/DECISIONS.md` (D-7, D-14), `docs/AUDIT.md`, the existing `cbt` and `api` apps.

## Tasks
- [ ] **5.1 Inspect and map (read only).** Document the existing question and attempt models, endpoints and what Flutter calls (`/api/cbt/`, `/api/questions`). Plan a non-destructive migration. Record the legacy-name exception (D-14).
- [ ] **5.2 Question bank (BE-08.1).** Additive fields: topic, difficulty, source, rights status, explanation. Per-question editing and bulk import in admin. **Correct answers are never serialised to a client before submission.**
- [ ] **5.3 Sessions (BE-08.2).** `PastQuestionsSession` (config, mode, seed, started_at, deadline, status) and `Answer`. Per-student question selection and ordering from the bank.
- [ ] **5.4 Practice mode (BE-08.3).** Immediate feedback and full review with explanations after submit; XP only per the published rule.
- [ ] **5.5 Competitive mode (BE-08.4).** Server issues the questions, owns the clock, rejects answers outside the window, scores objectively and records the official result. Stricter throttle scope `competitive`.
- [ ] **5.6 Theory marking (BE-08.5).** `MarkingTask` model; theory stays **off** unless D-7 says otherwise. No theory score is final until the workflow completes.
- [ ] **5.7 Tournaments (BE-08.6).** Topic, course, department and event challenges with published rules (question set, window, attempts, tie-break). Results feed Phase 4 boards.
- [ ] **5.8 Anti-cheating (BE-08.7, BE-15.5).** Attempt limits, per-student selection, anomaly flags for impossible completion times or repeated identical sessions; flagged awards go to a **quarantine** state excluded from boards until reviewed.
- [ ] **5.9 Performance data (BE-08.8) and XP.** Per-topic strengths and weak topics (`GET /api/v1/past-questions/performance`). All XP through `award_xp`; register the Past Questions validator for quests.
- [ ] **5.10 Migration (BE-08.9).** Written plan with row counts; migrate existing questions and attempt history without loss. Reversible. Test on a copy.

## Tests required
Competitive payload before submit contains no correct answers; clock enforcement (late answer rejected); two students in one tournament are scored identically; replay of a submission awards once; attempt limits; anomaly quarantines an award and removes it from boards; practice review works; legacy endpoints still return what Flutter expects.

## Acceptance (SRS)
In competitive mode, inspecting client traffic before submitting reveals no correct answers. A practice session can be reviewed afterwards with explanations for every question.

## Do not
Use "CBT" in new routes, models or copy; delete or rewrite existing questions or attempts; expose answer keys.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-05-past-questions.md. Do 5.1 first (read only) and report the existing models, endpoints and migration risks. Then plan 5.2 to 5.10 and wait for approval.
