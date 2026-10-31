# XP ledger and rewards: design note (Phase 3, task 3.1)

Status (31 Oct 2026): implementation is present in the real working tree and remains uncommitted. Historical scratch result: 58 tests passed, 1 PostgreSQL-only test skipped. Current repository validation is recorded in docs/PRESERVATION_REVIEW.md; scratch results are not current verification.
SRS: BE-04.1 to 04.7, DATA-04, API-04, D7. Owner: Israel. Reviewer: Javin.

Israel delegated every open decision ("take the best approach, comment it in the code", 30 Oct 2026). Each choice below is also commented where it lives in the code. Change any of them in review.

## Decisions taken

| ID | Choice | Where |
|----|--------|-------|
| D-1 | The real price list is in the Flutter code, which the build cannot see. Prices are seeded from past redemptions: each `reward_type` at its most common historical cost (ties: higher). **Israel must check every price in admin after the rehearsal.** A reward missing from the catalogue returns 400. | `rewards/migrations/0003_seed_reward_catalog.py` |
| D-2 | Two numbers from one ledger. Lifetime XP = award + adjustment + opening_balance (drives level). Spendable balance = every row. Spending never lowers a level. Opening balance = current points, so past redemptions are invisible to lifetime XP. | `xp/services.py` |
| D-12 | Conservative seed rules and a 10-level curve, editable in admin. `material_verified` = 10 XP, cap 50/day (the old +10). Other rules are unused until Phases 4 and 5. | `xp/migrations/0002_seed_rules_and_levels.py` |
| Season | No ledger season FK. D-17 supersedes the original nullable-FK plan: membership uses created_at in the season UTC window [starts_at, ends_at). | `seasons/services.py`, `leaderboards/boards.py` |
| Rule changes | Apply to new awards immediately. Season-boundary effective dates need Seasons (Phase 4). | `xp/models.py` |
| Client price | A `point_cost` sent by a client is silently ignored (older app builds keep working). | `rewards/views.py` |
| Capped awards | A capped award writes a zero-amount row. It holds the idempotency key, so replaying the event on a later day cannot pay out. | `xp/services.py` |
| Profile mirror | `UserProfile.points` is a write-only cache of the spendable balance, written only inside `xp.services`, so the live Flutter app (login payload, profile serializer) keeps working with no change to `accounts`. Remove it after the Release 1 gate. | `xp/services.py` |
| Adjustments | An admin adjustment may not take lifetime XP or the balance below zero. | `xp/services.py` |
| Extra endpoints | `GET /rewards/catalog` and `GET /rewards/redemptions` added (both in the API catalogue for Phase 3). | `rewards/v1_views.py` |

## Models

- `XPLedgerEntry`: user (PROTECT), signed amount, kind, reason_code, source_feature, source_record_id, idempotency_key, created_by (PROTECT), metadata, created_at. Unique (user, idempotency_key). A CHECK constraint ties the sign of the amount to the kind. Immutable: model `save`/`delete`, queryset `update`/`bulk_update`/`delete` all raise; admin is read-only. A database trigger would add a second lock; not done.
- `XPRule`, `LevelConfig`: configuration; admin edits need a reason and write an `AuditLog` row. No deletes.
- `RewardCatalog` (reward_type unique, point_cost, is_active). `Redemption.ledger_entry` (nullable one-to-one, PROTECT) links a redemption to its spend.

## Idempotency and locking

- Every write locks the student's auth row (`SELECT ... FOR UPDATE`), then checks the key, then the rule, cap and balance. SQLite ignores the lock, so the concurrency test only proves it on PostgreSQL.
- Same key and same request returns the existing row. Same key and a different request raises a conflict.
- v1 redeem: `Idempotency-Key` header (HTTP layer) and a derived ledger key (`redeem:<header>`). Legacy redeem has no client key, so one is generated; retries on that route are exactly as unsafe as before.

## Migration and rollback

1. `xp 0001` and `rewards 0002` create tables and the link. Additive.
2. `xp 0002` seeds rules and levels. Re-runnable, never overwrites edits. Reverse is a no-op.
3. `xp 0003` writes one opening row per student with points > 0. Batched, idempotent. Reverse deletes only its own rows and refuses if other ledger activity exists (then restore from backup).
4. `rewards 0003` seeds the catalogue. Re-runnable. Reverse is a no-op.

Migrations run on container start, so on deploy this runs on production unattended.

### Runbook before deploy (do not skip)

1. Restore a recent production backup to a throwaway database.
2. Point a LOCAL copy of the code at that copy only, run `python manage.py migrate`, then `python manage.py reconcile_points`.
3. Expect "Unexplained differences: 0". Open admin, Reward catalogue, and check every price.
4. Javin reviews. Only then merge and deploy.
5. After deploy, run `reconcile_points` on production. "explained: legacy write after cutover" rows mean the old container wrote points during the swap; fix each with an audited XP adjustment.

## What the build deliberately left for later

- `/me` returns `xp_level` and `xp_level_title` from the ledger; `/me/progress` returns `ledger_ready: true`, `xp_total` (lifetime), `level`, `level_title`, `xp_to_next_level`, `balance`. Ranks stay null until the Phase 4 boards (ledger profile integration recorded 30 Oct 2026; progress ranks remain null until task 4.9).
- Accounts' login payload and serializer still read `points`; the mirror keeps them correct.
- `UserProfile.points` is deprecated, not removed.
- The PostgreSQL concurrency test needs a PostgreSQL run.
- No test patches a material verification end to end (the `Material` model and its URL were not available); the award itself is covered through `xp.services`.

## API contracts (for Javin to mock against)

```
GET /api/v1/me/xp
Owner: Israel | Consumers: Flutter, Web | Auth: required
Query: page_size (default 20, max 100), cursor
200: { "results": [ { id, amount, kind, reason_code, source_feature, created_at } ],
       "next_cursor": "<token>|null",
       "summary": { lifetime_xp, balance, level, level_title, xp_to_next_level|null } }
Errors: 401 | 429. Read-only. Newest first. `summary` repeats on every page.

POST /api/v1/rewards/redeem
Auth: required | Idempotency-Key: required
Request: { reward_type, phone, network }   (a point_cost is ignored)
201: { id, username, reward_type, point_cost, phone, network, status, created_at }
Errors: 400 validation_error (reward_type not available, or points: insufficient) | 401 | 409 conflict | 429

GET /api/v1/rewards/catalog        Auth: required
200: { "results": [ { reward_type, point_cost } ], "next_cursor": ... }   active rewards, cheapest first

GET /api/v1/rewards/redemptions    Auth: required
200: { "results": [ redemption ], "next_cursor": ... }   the caller's own only

Legacy POST /api/rewards/redeem/ keeps its request and response shapes. Changes:
point_cost is ignored (catalogue price charged); unknown reward_type is 400 {"error": ...}.
```
