# Phase 10: Courses, RAG and audio

**Release:** R2 (flag off until gate; pipeline design in R1) | **SRS:** BE-09.1 to 09.9, DATA-08, NFR-C1/C2, section 11 | **Owner:** Israel | **Size:** XL | **Depends on:** 3, 4, 6

## Goal
Courses built from approved material, explained by AI **grounded in that material**, delivered as reusable audio. Cost is a first-class concern.

## Read first
`docs/DECISIONS.md` (D-9), SRS BE-09 and section 11 (rights, provider terms), the existing `course`, `materials` and `aiassistant` apps.

## Tasks
- [ ] **10.1 Design note.** `docs/design/courses-rag-audio.md`: models, chunking, embedding and vector store choice (D-9), provider options (Bedrock models are already configured), a per-section cost estimate (NFR-C1), and the job pipeline. **Wait for approval** before building.
- [ ] **10.2 Course models (BE-09.1).** `Course`, `CourseSection` (ordered), `SourceMaterial` (with rights status and version), owning faculty/department, publish state. Admin authoring.
- [ ] **10.3 Rights gate (BE-09.2, section 11).** Ingest only material whose written basis is recorded. Existing materials migrate in only where rights are confirmed.
- [ ] **10.4 Retrieval index.** Chunk approved material with source references kept per chunk.
- [ ] **10.5 Grounded explanations (BE-09.3, 09.8).** Retrieval first; the generator receives the passages; the explanation stores which sources it used; unsupported content is flagged. Review queue: approve, edit, regenerate, reject. **No unreviewed AI explanation is published.**
- [ ] **10.6 Audio jobs (BE-09.4, 09.5).** Two modes: AI-explained and direct reading, as background jobs. Cache per section version; later students get the existing approved audio; regenerate only when the source version changes or an admin asks. Stale audio is never served silently.
- [ ] **10.7 Progress and XP (BE-09.6, 09.7).** Per-student section progress and checkpoints; resumable audio position; one course endpoint with sections and progress. XP only through `award_xp` on validated completion. Register the course-progress quest validator.
- [ ] **10.8 Cost tracking (BE-09.9).** Record AI and speech usage per section; report cost per active learner for the analytics dashboard; alerts at thresholds (NFR-C2).
- [ ] **10.9 Lumora grounding.** Make the assistant use the same retrieval discipline where practical (SRS 3.4).

## Tests required
Second student gets cached audio with no new generation; every published explanation lists its source passages; changing source marks audio stale and queues regeneration; unapproved explanation never served; rights-blocked material is not ingested; completion awards XP once.

## Acceptance (SRS)
As listed above under tests, plus: cost per section is recorded and visible.

## Do not
Send student personal data to AI providers; call paid AI or speech services in tests (mock them); enable the flag; start before the design note is approved.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-10-courses-rag-audio.md. Produce only the design note and cost estimate (10.1). Ask me about D-9. Wait for approval before any code.
