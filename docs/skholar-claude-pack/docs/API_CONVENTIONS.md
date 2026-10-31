# API conventions and endpoint catalogue

Source: SRS section 9. Contract first (API-02): write the contract here **before** building an endpoint, and Javin reviews it so Flutter and the web world can mock against it.

## Rules (from the SRS)

- **API-01** Versioned REST under `/api/v1/`, JSON over HTTPS. Real-time is a separate channel and never carries authoritative awards.
- **API-03** Every list endpoint paginates and supports the filters its screen needs. One pagination pattern everywhere (see D-4).
- **API-04** Award, submission and completion endpoints accept an idempotency key and are safe to retry.
- **API-05** Breaking changes ship as a new version. Old Flutter clients keep working. Legacy `/api/...` routes stay untouched.
- **API-06** One error shape everywhere: machine `code`, human `message`, `field_errors` where relevant, and a `request_id` that also appears in server logs.
- **API-07** Documented rate limits; stricter on auth and competitive endpoints.
- Every v1 endpoint is **authenticated unless explicitly marked public**. Object-level authorisation on every read and write.

confirmed now in Phase 1

## Error shape (confirmed in Phase 1)
`field_errors` is always present and is `{}` when empty. Codes: `validation_error`,
`bad_request`, `not_authenticated`, `token_not_valid`, `permission_denied`, `not_found`,
`method_not_allowed`, `conflict`, `rate_limited`, `server_error`, `service_unavailable`.
Every response (v1 and legacy) carries an `X-Request-ID` header; v1 error bodies repeat it as `request_id`.

## Pagination (D-4)
- Cursor (`V1ListAPIView`): `?page_size=` (default 20, max 100), `?cursor=`. Response:
  `{"results": [...], "next_cursor": "<token>|null"}`. Newest first, `id` tie-break. Stop when `next_cursor` is null.
- Page number (`V1AdminListAPIView`, small admin lists only): `?page=`, `?page_size=`. Response:
  `{"count","page","page_size","total_pages","results"}`.
- A bad `cursor` or `page` is a 400 `validation_error` naming the parameter.

## Idempotency (API-04)
Award, submission and completion endpoints require header `Idempotency-Key` (1 to 128 chars: letters,
digits, `.`, `_`, `:`, `-`). Same key + same request replays the stored 2xx response with header
`Idempotent-Replayed: true`. Same key + different request is 409 `conflict`. Only 2xx responses are
stored; any other outcome frees the key. The ledger (BE-04.3) is the real double-award guard.

## Rate limits (API-07)
`v1_default` 120/min, `v1_auth` 10/min, `v1_competitive` 30/min. Per user when logged in, per IP otherwise.
429 returns `rate_limited` plus `Retry-After`. Health and ready are not limited.

## Paths and platform endpoints
Catalogue paths have no trailing slash; routes accept both. `GET /api/v1/health` (liveness, no DB) and
`GET /api/v1/ready` (DB check, 503 `service_unavailable` when down) are public.
Feature flags and settings are managed in Django admin with a mandatory reason, written to the audit log.

```json
{
  "code": "validation_error",
  "message": "Please correct the highlighted fields.",
  "field_errors": { "department": ["This field is required."] },
  "request_id": "9f2c1c0e-..."
}
```

## Contract template (copy per endpoint)

```
METHOD /api/v1/path
Owner: Israel | Consumers: Flutter, Web
Auth: required | public | admin
Request: { ... }
Response 200/201: { ... }
Errors: 400 validation_error | 401 | 403 | 404 | 409 conflict | 429 rate_limited
Idempotency: header Idempotency-Key (required | n/a)
Notes: ...
```

## Catalogue (minimum; design may add, never silently remove)

Paths are relative to `/api/v1`.

| Area | Endpoints | Phase |
|------|-----------|-------|
| Platform | GET /health, GET /ready | 1 |
| Auth | POST /auth/world-handoff (+ exchange), existing login/refresh/reset stay on legacy routes until a v1 equivalent is agreed | 2 |
| Profile and identity | GET/PATCH /me, GET /me/progress, GET /faculties, GET /departments, POST /me/department-change | 2 |
| Progression | GET /me/xp, GET /leaderboards/{scope}/{period}, GET /seasons/current, GET /scoring-rules | 3, 4 |
| Rewards | POST /rewards/redeem, GET /rewards/catalog, GET /rewards/redemptions | 3 |
| Quests and events | GET /quests/for-me, POST /quests/{id}/accept, POST /quests/{id}/complete, GET/POST /events/* | 4 |
| Past Questions | GET /past-questions/topics, POST /past-questions/sessions, GET /past-questions/sessions/{id}, POST .../answers, POST .../submit, GET /past-questions/performance | 5 |
| Feed and news | GET /feed, GET /news/{id}, POST /feed/{id}/interaction | 6 |
| Notifications | GET /notifications, POST /notifications/{id}/read, GET/PATCH /me/notification-preferences, POST /devices/push-token | 6 |
| Moderation | POST /reports | 6 |
| Badges and social (R2) | GET /me/badges, POST /friends/requests, POST /friends/{id}/accept, POST /blocks, GET/PATCH /me/visibility | 8 |
| Classrooms (R2) | POST /classrooms, POST /classrooms/join, GET /classrooms/{id}, POST /classrooms/{id}/assignments, POST /classrooms/{id}/rotate-code | 9 |
| Courses and audio (R2) | GET /courses, GET /courses/{id}, GET /sections/{id}/audio/{mode}, POST /sections/{id}/progress, GET /me/continue-learning | 10 |
| Business (R3) | GET /businesses, GET /listings, POST /enquiries | 12 |
| Location (R3, flag off) | POST /location/share/start, POST /location/share/stop, GET /location/visible-to-me | 12 |
| Admin | /admin/* equivalents for each area, role-gated and audited | each phase |

Avatar (`/me/avatar`, schema, assets map) and world content (`/world/manifest`, `/pois`, check-in) are **Javin's** (BE-03, BE-18). The backend phases only provide the contract hooks they need.

## Phase 2 contracts (built)

GET /api/v1/faculties, GET /api/v1/departments?faculty_id=  (public, page-number paginated, active rows only)
  Faculty: { id, name, code }   Department: { id, name, code, faculty_id }

GET /api/v1/me   (auth)
  { id, username, display_name, avatar:null, xp_level:null, badges:[], faculty, department, academic_level,
    private:{ email, first_name, last_name, phone, network, student_id, matric_number },
    profile_complete, missing_fields }
PATCH /api/v1/me  any of first_name, last_name, phone, network, student_id, matric_number; any other key is a 400 field error.

GET /api/v1/me/progress  (auth)
  { ledger_ready:false, xp_total, level, xp_to_next_level, personal_rank, department_rank (null until Phase 3/4),
    department, suggested_activities:[], profile_complete, missing_fields }

POST /api/v1/me/department-change  (auth)  { department_id, level_id?, reason? }  -> same body as GET /me
  400 validation_error, 409 conflict (already changed this semester; admin approval needed)

POST /api/v1/auth/world-handoff  (auth, v1_auth throttle) -> 201 { token, expires_in }   (Cache-Control: no-store)
POST /api/v1/auth/world-handoff/exchange  (public) { token } -> 200 { access, refresh, user:{id, username} }
  400 bad_request "invalid or expired" (one message for every failure)

GET /api/v1/me/export  (auth, v1_auth throttle) -> the student's own data as JSON (attachment, no-store)

Legacy responses that changed behaviour (bodies unchanged):
  POST /api/token/  -> 429 {"detail": "Too many failed attempts. Try again in N minute(s)."} + Retry-After
  /api/password_reset/, /confirm/, /validate_token/ -> 429 when limits are hit; code lifetime 15 minutes

## Phase 4 contracts (built)

```
GET /api/v1/scoring-rules[?university_id=]
Owner: Israel | Consumers: Flutter, Web | Auth: required (suspended students may read)
Default scope: the caller's own university (via faculty); else the global rule.
200: { "rule_set": null }                       nothing published (drafts are never returned)
200: { "rule_set": {
         id, name, scope: "global"|"university", university: {id,name,code}|null,
         summary,                                show verbatim
         student_cap: int|null, uncapped: bool,  exactly one is set: a cap, or uncapped=true
         activated_at,
         activities: [ { action_code, label, weight: "1.50", per_student_cap: int|null } ] } }
Errors: 400 validation_error (university_id not a number) | 401 | 404 not_found (unknown/inactive university) | 405 | 429
Idempotency: n/a (read-only)
Notes: weight is a decimal string = contribution points per 1 XP from that activity. Caps are in
contribution points. Rules change only by activating a new rule set (old one is retired, never edited).
```

```
GET /api/v1/leaderboards/{scope}/{period}
Owner: Israel | Consumers: Flutter, Web | Auth: required, not suspended (403 permission_denied)
scope: department | faculty | university      period: lifetime | week | season
Query: offset (default 0), limit (default 10, 1..100), around (default 2, 0..10),
       top (default 10, 0..100; 0 = omit)                       Phase 4.4
       department_id | faculty_id (another unit in the caller's OWN university; default = the caller's own),
       season_id (an open or closed season of the period's kind; default = the open one)
200: { scope, period,
       university: {id,name,code}|null, unit: {id,name,code}|null,
       season: {id,name,kind,state,starts_at,ends_at}|null,     null for lifetime, or no open season
       total, offset, limit, next_offset: int|null,
       me: entry|null,                                          null = caller has no XP on this board
       top: [entry],                                             positions 1..top, NOT affected by offset (Phase 4.4)
       entries: [entry],                                         positions offset+1..offset+limit (offset 0 = top)
       around_me: [entry] }                                      caller +/- `around` positions
entry: { rank, position, user: {id, username, display_name}, xp, is_me }
Errors: 400 validation_error (bad offset/limit/around/top/ids; season_id on lifetime) | 401 | 403 |
        404 not_found (unknown scope/period; unit outside the caller's university; unknown or scheduled season) | 405 | 429
Idempotency: n/a (read-only)
Notes: xp = award XP earned in the window (D-19). Spends, adjustments and opening balances never count.
Exclusions (BE-05.5, Phase 4.5, D-22): suspended and deleted accounts are left off every board, and a
quarantined award is left out of the score (the student's other awards still count; a student whose
only awards are quarantined is not on the board, so `me` is null). Applies to top, entries, me,
around_me and total alike. Exclusion is read-time only: ledger history, balance and level are unchanged.
There is no public quarantine endpoint (admin only, audited); the review workflow arrives in Phase 5.8.
rank is shared by ties (1, 1, 3); position is unique (tie order = user id). Windows are UTC [starts_at, ends_at).
BE-05.3 (Phase 4.4): `top`, `entries`, `me` and `around_me` come from ONE board query; the lists may
overlap (the same entry can appear in several), so clients render each list on its own.
"Your position" screen: one call with defaults gives the top 10, the caller and 2 either side.
`top` is additive: clients that ignore it keep working unchanged.
A caller with no faculty/department gets unit=null and empty lists for that scope (show "complete your profile").
Collective boards (D-18) and archived snapshots (4.6) are not part of this endpoint yet.
```

