# Phase 3: XP ledger and rewards

**Release:** R1 | **SRS:** BE-04.1 to 04.7, DATA-04, DATA-18, API-04, D7 | **Owner:** Israel | **Size:** XL | **Depends on:** 1, 2

## Goal
Replace the single `UserProfile.points` integer with an append-only ledger that is auditable, idempotent and cap-aware, rebuild redemption on it with **server-owned prices**, and migrate existing balances with a reconciliation report. **This is the highest-risk phase. Go slowly and test hard.**

## Read first
`docs/DECISIONS.md` (**D-1 and D-2 are BLOCKING**, D-12), `docs/AUDIT.md` section (a) (every writer of `points`).

## Tasks
- [ ] **3.1 Design note.** Write `docs/design/xp-ledger.md`: models, constraints, the lifetime-XP versus spendable-balance rule (D-2), idempotency scheme, locking strategy, migration and rollback plan. **Wait for Israel's approval.**
- [ ] **3.2 Models.** New app `xp`: `XPLedgerEntry` (user FK **PROTECT**, signed amount, kind: award / spend / adjustment / opening_balance, reason_code, source_feature, source_record_id, idempotency_key, created_by nullable, created_at, metadata JSON, season nullable), `XPRule` (action code, amount, daily cap, diminishing-returns config), `LevelConfig` (level number, XP threshold, title, effective_from). Unique constraint for idempotency. Ledger rows are never updated or deleted: block it in the model, a custom manager and queryset, and read-only admin.
- [ ] **3.3 Service layer.** `xp/services.py`: `award_xp(...)`, `spend_points(...)`, `get_balance(user)`, `get_lifetime_xp(user)`, `get_level(user)`. Each runs in a transaction; spending locks the user row (`select_for_update`) before checking the balance. Daily caps and diminishing returns use the Africa/Lagos day. Replaying the same source event returns the existing row.
- [ ] **3.4 Seed defaults** (D-12) as data: rules and level curve, editable in admin, changes audited, effective for new awards without a deploy (BE-04.4, BE-20.1).
- [ ] **3.5 Reward catalogue.** `RewardCatalog` (reward_type, point_cost, active) seeded from the real values (D-1). The server decides the price.
- [ ] **3.6 Redeem rebuild.** Legacy `/api/rewards/redeem/` becomes a thin wrapper: **ignore any client `point_cost`**, look up the catalogue, call `spend_points`, create the `Redemption` linked to its ledger row. Keep the legacy response shape. Add `POST /api/v1/rewards/redeem` with an `Idempotency-Key`. Unknown `reward_type` returns 400.
- [ ] **3.7 Move every other points writer** (from AUDIT.md) onto the service. `UserProfile.points` stops being written; any serializer that exposes it returns the ledger-computed balance so the Flutter app keeps working. Make the field read-only in admin.
- [ ] **3.8 Opening balances.** Separate, reversible, idempotent data migration (batched) writing one `opening_balance` row per student with `points > 0`. Management command `reconcile_points` with `--dry-run`, producing old total, new total and per-student differences with explanations. **Test on a copy of the data, never on production from a laptop.**
- [ ] **3.9 Admin adjustment (BE-04.7).** Award or deduct with a mandatory reason; writes a ledger row and an `AuditLog` entry. Direct balance edits are impossible.
- [ ] **3.10 Read endpoint.** `GET /api/v1/me/xp`: lifetime XP, spendable balance, level, XP to next level, recent entries (paginated).

## Tests required
Replay awards once; negative and zero costs rejected; balance recomputed from the ledger equals what clients see; daily cap and diminishing returns; ledger rows cannot be updated or deleted; concurrent double-spend (PostgreSQL only, `skipUnless`); legacy redeem still works for the old payload but cannot mint points; opening-balance migration idempotent and reversible; reconciliation report zero unexplained differences on seeded data.

## Acceptance (SRS)
Submitting the same completed event twice awards XP once. Recomputing any student's balance from the ledger matches both clients. The reconciliation report shows zero unexplained differences.

## Do not
Store a trusted balance column; use CASCADE on ledger user FKs; run the migration against production; remove `UserProfile.points` yet (deprecate first, remove after the Release 1 gate).

## Start prompt
> Read CLAUDE.md and docs/phases/phase-03-xp-ledger-and-rewards.md. Ask me for D-1 and D-2 first. Then produce the design note (3.1) only and wait for approval. Do not write models until I approve it.
