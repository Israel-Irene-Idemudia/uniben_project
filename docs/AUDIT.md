# Audit (Phase 0, task 0.6)

Date: 27 Oct 2026. Branch: `skholar-world-dev`.
Source read: a `git archive` zip taken at commit `7028e4a` (before the Phase 0 commits `42f0971`, `82a71d5`, `1b6dcaa`, `52b5110`), excluding PDFs, Word files, `media/`, `staticfiles/` and `.pyc`.
Not checked: `admin.py` files, `signals.py`, migrations, the live database, the live server and the Flutter app. Anything marked "unknown" needs Israel or Javin.

## 1. Findings, by priority

| # | Finding | Where | Status |
|---|---------|-------|--------|
| F1 | `/media/<path>` served project source files because `MEDIA_ROOT` was never set (Django defaults it to the working directory). Confirmed live on 27 Oct 2026 (`/media/uniben_portal/urls.py` returned the file). | `uniben_portal/urls.py`, `settings.py` | Fixed in `82a71d5`, with a test. **Not deployed.** Live site stays exposed until it is. |
| F2 | Default admin login. `create_superuser.py` creates user `admin` with password `admin123` unless `SUPERUSER_PASSWORD` is set. `build.sh` runs it on every build and `render.yaml` sets `CREATE_SUPERUSER`. | `create_superuser.py`, `build.sh`, `render.yaml` | **Open.** Reset the live `admin` password. |
| F3 | Any logged-in student can create, edit and delete courses and questions. `CourseViewSet` and `QuestionViewSet` are full `ModelViewSet`s with `IsAuthenticatedOrReadOnly`. `QuestionSerializer` also exposes `answer`, so anonymous readers see correct answers. | `api/views.py`, `api/serializers.py` (routes `/api/courses/`, `/api/questions/`) | **Open.** Fix needs a legacy-compatibility check with Javin (D-11). |
| F4 | `upload_file` is `@csrf_exempt`, has no authentication, no size or type limit, saves to default storage, then extracts text (and may call an AI provider). Anonymous abuse means storage and AI cost. | `aiassistant/views.py` (route `/api/aiassistant/upload/`) | **Open.** Fix needs a check that the Flutter app sends a token. |
| F5 | Redeem price is set by the client (`point_cost`). Negative and zero are now rejected; underpricing (for example `point_cost=1`) is still possible. | `rewards/views.py` | Deferred to Phase 3 (D-1) by Israel's decision. |
| F6 | Material verification awards +10 points and is not idempotent (unverify then verify again awards again). Admin only. No ledger row. | `materials/views.py` line 120 | Log for Phase 3. |
| F7 | Settings risks, see section 6. | `settings.py` | Mixed. |
| F8 | `.env.example` had a real RDS hostname and username on line 22. | `.env.example` | Replaced with placeholders in `52b5110`. Old value remains in git history. |

## 2. (a) Reads and writes of `UserProfile.points`

| File | Kind | What |
|------|------|------|
| `rewards/views.py` | write (subtract) | Redeem endpoint, under `select_for_update` inside `transaction.atomic` |
| `materials/views.py:120` | write (+10) | Admin verification of a material, no idempotency |
| `accounts/views.py:34` | read | Login payload (`data['points']`) |
| `accounts/serializers.py` | read | `UserProfileSerializer` exposes `points`; `pending_points` is unverified materials times 10 |
| `accounts/models.py:18` | definition | `points = IntegerField(default=0)` |

`UpdateProfileSerializer` does not include `points`, so a client cannot set its own points through profile update. Direct edit through Django admin was not checked (`accounts/admin.py`).

## 3. (b) Exposed URLs and permission classes (D-11 compatibility list)

Root prefixes: `api/` is shared by `news`, `events`, `materials` and `api`. `api/courses/` (app `api`) and `api/core/courses/` (app `core`) are different routes.
Default permission class when a view sets none: `IsAuthenticatedOrReadOnly`.

| Prefix | Endpoints | Permission |
|--------|-----------|------------|
| `/admin/tps/` | Django admin | Django staff login |
| `/api/token/`, `/api/token/refresh/` | JWT login and refresh | public |
| `/api/password_reset/` | `django-rest-passwordreset` | public |
| `/api/accounts/` | `register/` | public |
| | `me/`, `profile/update/`, `delete/`, `profile/timetable|todos|notes|gpa|debater|preferences/` (+ bulk-sync) | authenticated |
| | `users/`, `users/<id>/` | authenticated plus manual `is_staff` check in the view |
| | `deletion-requests/`, `deletion-requests/<id>/action/` | admin |
| `/api/rewards/` | `redeem/`, `redemptions/` | authenticated |
| | `admin/list/`, `admin/dispatch/<id>/` | admin |
| `/api/` (api app) | `courses/`, `questions/` (+ `courses/<id>/questions/`, `courses/<id>/submit/`) | **read public, write any authenticated user (F3)** |
| `/api/core/` | `faculties/`, `departments/`, `course-areas/`, `levels/`, `courses/`, `locations/` | public, read only |
| | `contact/` | public create |
| | `contact/list/`, `contact/<id>/`, `contact/<id>/reply/` | admin |
| | `global-prompt/` | GET public, writes admin |
| `/api/cbt/` | `courses/<id>/exams/` | read public |
| | `my-courses/`, `<exam_id>/start/`, `sessions/<token>/autosave/`, `sessions/<token>/submit/` | authenticated |
| | `debater-questions/` | public |
| `/api/aiassistant/` | `upload/` | **public, csrf exempt (F4)** |
| | `lumora-chat/`, `cbt-explanation/`, `pdf-summary/` | authenticated |
| `/api/notifications/` | `in-app/*`, `support/create/` | authenticated |
| | `broadcast/`, `in-app/send/`, `support/list/`, `support/<id>/` | admin (custom `IsAdminUser`) |
| `/api/analytics/` | `track/` | authenticated |
| | `stats/`, `students-breakdown/`, `today-joiners/`, `user-details/<id>/` | admin |
| `/api/` (events, news) | `events/*`, `news/*` | read public, write admin |
| `/api/` (materials) | `materials/`, `materials/<category>/` | default (read public) |
| | `materials/upload/`, `materials/user/` | authenticated |
| | `admin/materials/*` | admin |
| `/media/<path>` | file serve (when `DEBUG` is off) | public; now confined to `BASE_DIR/media` by `82a71d5` |

Legacy `/api/...` routes stay untouched (CLAUDE.md rule 6). New endpoints go under `/api/v1/`.

## 4. (c) Avatar data today

None. No `avatar` field or model exists in the backend (searched all `.py` and `.json`). BE-03 (Javin) will add the avatar config.

## 5. (d) Model inventory and user-linked `CASCADE`

| App | Models |
|-----|--------|
| accounts | UserProfile, UserTimetableEntry, UserPreferences, UserTodoEntry, UserNoteEntry, UserGpaEntry, UserDebaterProgress, AccountDeletionRequest |
| core | Faculty, Department, CourseArea, Level, Course, ContactMessage, CampusLocation, GlobalPrompt |
| api | Course, Question (a second, older course/question pair) |
| course | Course (a third course model) |
| cbt | Exam, Question, Option, ExamQuestion, ExamSession, DebaterQuestion |
| events | Event |
| materials | Material |
| news | News |
| notifications | InAppNotification, SupportTicket |
| aiassistant | AIUploadLog, StudentAIPromptTracker |
| app_analytics | UserActivity |
| rewards | Redemption |

**User FKs with `on_delete=CASCADE`** (deleting a user deletes these rows): UserProfile, UserTimetableEntry, UserPreferences, UserTodoEntry, UserNoteEntry, UserGpaEntry, UserDebaterProgress, AccountDeletionRequest, ContactMessage (nullable), Material.user (nullable), cbt.ExamSession.student, AIUploadLog, StudentAIPromptTracker, UserActivity, Redemption.user. InAppNotification and SupportTicket also use CASCADE on a user FK (the file was read by pattern only, so confirm).

**Why it matters:**
- The XP ledger must use `PROTECT` on the user FK (CLAUDE.md). Account deletion (BE-01.6) must anonymise, not delete, so ledger and audit history survive.
- `Redemption` rows disappear when a user is deleted today.
- Structural cascades: deleting a `core.Department` deletes its `Level`s, `CourseArea`s and `Course`s, and a `core.Course` deletion cascades to `cbt.Exam` and `cbt.ExamSession` (student results). The registry (BE-02.1) should use an `active` flag, not deletes.
- Three separate `Course` models (`core`, `api`, `course`) and two `Question` models (`api`, `cbt`) exist. Past Questions (Phase 5) needs a decision on which is canonical.
- `core.Level` is the academic level (100L); XP levels must be named `XP...` or `LevelConfig`.

## 6. (e) How deploy and migrations run

Facts from the files:
- `Dockerfile` (python 3.11-slim, `WORKDIR /app`, `COPY . .`): `CMD python manage.py migrate --noinput && gunicorn uniben_portal.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2`. Migrations run on every container start.
- `uniben_portal/wsgi.py`: runs `migrate` at import when a `RENDER` environment variable is set (the check is redundant: `== 'true' or is not None`). Not triggered on AWS unless that variable exists.
- `render.yaml` (two copies: repo root and `uniben_portal/static/render.yaml`): runs `collectstatic` and `migrate` at build and sets `CREATE_SUPERUSER`. Render hosting is believed stale. The copy under `static/` is served publicly by WhiteNoise.
- `build.sh`: runs `migrate`, then `loaddata initial_data.json` and `loaddata cbt_questions.json` (both `|| true`), `collectstatic`, then `create_superuser`. **If this script runs on production, fixture reloads can overwrite admin-edited rows with the same primary keys.** Unknown whether it is used.
- `setup_ec2.sh`: Ubuntu setup with nginx, a gunicorn systemd socket (3 workers, `/var/www/skholar`), and server name `api.skholar.site`. It does not run migrations.
- `.dockerignore` excludes `.env`, `media/`, `staticfiles/`, `*.sqlite3`.
- No `.github/workflows` directory exists in the archive.

Unknown (D-10, owner Israel): where production runs (EC2 with nginx, or a container service), which branch deploys and how, who runs migrations, and whether a real staging environment exists (a branch is not one). Until answered, treat every migration reaching a deployed branch as live.

## 7. (f) Settings risks (`uniben_portal/settings.py`)

1. `DEFAULT_PERMISSION_CLASSES` is `IsAuthenticatedOrReadOnly`, so any view without its own permission class is publicly readable.
2. No throttling anywhere (API-07).
3. Root logger at `DEBUG` level, which can log request details and library internals.
4. `SECRET_KEY` has an insecure default (`django-insecure-dev-secret`). JWTs are signed with it, so a missing environment variable silently weakens every token. Rotating it logs everyone out.
5. `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `ONESIGNAL_*` and `CLOUDINARY_*` have no default, so the app will not start without them.
6. `IS_TESTING` is true if any command-line argument contains the text "test" (for example a path with `latest`). In production that would switch to SQLite and `FileSystemStorage`.
7. `STATICFILES_STORAGE` and `DEFAULT_FILE_STORAGE` were removed in Django 5.1, so they are ignored on 5.2. Cloudinary storage is forced at runtime by manually replacing `default_storage` in `settings.py` and `uniben_portal/cloudinary_override.py`. Fragile; do not touch without tests.
8. No HTTPS hardening settings (SSL redirect, HSTS, secure cookies).
9. `CORS_ALLOWED_ORIGIN_REGEXES` allows any localhost port in production; `CORS_ALLOWED_ORIGINS` is built from `"".split(",")`, which yields an empty string entry when the variable is unset.
10. `DATA_UPLOAD_MAX_MEMORY_SIZE` is 100 MB for every endpoint.
11. Startup `print` statements show the Cloudinary cloud name.
12. `MEDIA_ROOT` was unset (F1, fixed).

## 8. Repo hygiene notes

- Stray files in the repo root: `_toBlock(m[1]!.trim())` and `backend/uniben_project/core/admin.py`. Do not delete without Israel's approval.
- Untracked in the working folder: `avatar_usage.txt`, `points_usage.txt`, `tree.txt`, `materials/test_doc_*.pdf`.
- Tracked `.pyc` files were removed from the index in `1b6dcaa`.
- Course PDFs and Word files under `materials/` and `media/` may be tracked. Their rights status is unrecorded (SRS section 11). Run `git ls-files` and list them here.

## 9. Proposed next actions (each needs approval)

1. Deploy the `MEDIA_ROOT` fix (or block `/media/` at the server) and tell Javin.
2. Reset the live `admin` password; make `create_superuser.py` fail when `SUPERUSER_PASSWORD` is unset.
3. Lock `/api/courses/` and `/api/questions/` writes to admins and hide `answer` from non-admins, after Javin confirms what the Flutter app calls.
4. Require authentication and limits on `/api/aiassistant/upload/`, after Javin confirms the app sends a token.
5. Answer D-10 before Phase 7; answer D-1 and D-2 before Phase 3.
