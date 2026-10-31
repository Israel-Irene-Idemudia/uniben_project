# Phase 6: Feed, notifications, moderation and analytics hooks

**Release:** R1 | **SRS:** BE-11, BE-14, BE-15, BE-20.3, BE-12.2 (communities, minimal), BE-17.1 (server-side emission only) | **Owner:** Israel | **Size:** L | **Depends on:** 2, 3, 4, 5

## Goal
Make the home feed, notifications and safety paths real. Every social or content feature ships with its moderation path in the same release.

## Read first
`docs/DECISIONS.md` (D-5), the existing `news`, `notifications` and `app_analytics` apps.

## Tasks
- [ ] **6.1 News and feed items (BE-11.2).** Extend `news` with verification state, publish and expiry. Only verified items are served as news.
- [ ] **6.2 Feed assembly (BE-11.1, 11.3).** `GET /api/v1/feed`: ranked, capped (cap from `PlatformSetting`), each item with order, duration hint and deep link, so both clients can show a status sequence or a list. `POST /feed/{id}/interaction` records seen, opened, skipped, clicked without marking un-seen items as read.
- [ ] **6.3 Recommendations (BE-11.5).** From the student's own activity only (weak topics from Phase 5, unfinished items, department quests), labelled as recommendations.
- [ ] **6.4 Notification inbox (BE-14.2).** `Notification` (inbox is the authoritative record) and `NotificationPreference` (quiet hours, daily cap, per-category opt-out, security notices exempt). `GET /notifications`, `POST /notifications/{id}/read`, `GET/PATCH /me/notification-preferences`, `POST /devices/push-token`.
- [ ] **6.5 Triggers and delivery (BE-14.1, 14.3, 14.4).** Quest expiring, event starting, season closing for now (badge and classroom triggers arrive in Phase 8 and 9). OneSignal push is a delivery attempt on top of the inbox; a push failure never loses the notification. Frequency caps enforced.
- [ ] **6.6 Reports and moderation (BE-15.1, 15.2).** `Report` (category, target, reporter) from any surface; `ModerationAction` (warn, hide, suspend feature, suspend account, dismiss) each with a mandatory reason and an `AuditLog` entry. Suspension integrates with the Phase 2 account states. Appeal and contact route (Should, BE-15.3).
- [ ] **6.7 Anomaly queue (BE-15.5, BE-05.5).** Review queue for quarantined progression with clear and confirm actions.
- [ ] **6.8 Background jobs (BE-20.3).** Run feed assembly, notification fan-out and board computation as jobs per D-5, with retries and failure visibility in admin; no user request blocks on a job.
- [ ] **6.9 Analytics hooks and communities.** Reuse `app_analytics`: emit the server-side events the backend owns (onboarding, quest, Past Questions, leaderboard, feed). Javin's BE-17 owns the dashboard, so only provide the emission service and event names. Never record precise location (BE-17.4). Minimal department/faculty community endpoints from the registry (BE-12.2).

## Tests required
Unverified news never appears; feed never exceeds its cap; preferences and quiet hours respected; push failure leaves the inbox row; every moderator action traceable to actor, reason and time; suspended account loses competitive access and boards; interactions do not mark unseen items as read.

## Acceptance (SRS)
Publishing a news item in admin makes it appear with no deploy. Turning off quest notifications stops pushes but items remain in the inbox and feed.

## Do not
Fabricate "trending" labels; add DMs between strangers (BE-12.4); build the analytics dashboard (that is Javin's).

## Start prompt
> Read CLAUDE.md and docs/phases/phase-06-feed-notifications-moderation.md. Inspect the existing news, notifications and app_analytics apps and report what can be reused. Then plan 6.1 to 6.9 and wait for approval.
