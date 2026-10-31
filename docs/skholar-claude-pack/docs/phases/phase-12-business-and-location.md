# Phase 12: Business discovery and live location

**Release:** R3 (flags off until the Release 3 gate; location needs its privacy sign-off first) | **SRS:** BE-19.1, BE-19.2, BE-16.1 to 16.7, BE-13 (backend support), DATA-14, DATA-15, section 11 | **Owner:** Israel (BE-13 is Javin's) | **Size:** L | **Depends on:** 8, 11

## Goal
Let students find verified campus businesses, and build opt-in live location with the strictest privacy rules in the product. **No payments anywhere.**

## Part A: Business discovery (BE-19.1, 19.2)
- [ ] **12.1 Models.** `Business` (name, category, description, POI link, enquiry route, verification state), `Listing`, categories. Searchable and browsable.
- [ ] **12.2 Endpoints.** `GET /api/v1/businesses`, `GET /listings`, `POST /enquiries`. **No order, payment or escrow code at all** (BE-19.3 to 19.5 are Release 4).
- [ ] **12.3 Admin moderation.** Merchant verification, listing moderation, takedown, all audited. Reports on listings route to Phase 6 moderation.

## Part B: Live location (BE-16)
- [ ] **12.4 Design note and privacy review prep.** `docs/design/location-sharing.md`: data minimised, retention named, audience rules, expiry. Prepare the Nigeria Data Protection Act 2023 review pack (BE-16.6). **Wait for approval.**
- [ ] **12.5 Share sessions (BE-16.1 to 16.3).** `LocationShareSession` with minimal fields only (user, audience, start, expiry). Off by default; started only by an explicit action; audience limited to friends, department or room members (**no "everyone"**); auto-expires and stops on toggle-off, backgrounding beyond the grace period, or leaving the campus area.
- [ ] **12.6 Serving rules (BE-16.4, 16.5).** Live position is **not** stored as history. Locations are served only to the chosen audience while sharing is active; after expiry the response contains no location.
- [ ] **12.7 Isolation (BE-16.7, BE-17.4).** A student who never enables sharing loses nothing. Analytics never receives precise location.
- [ ] **12.8 Presence support (BE-13, Javin's).** Only the backend hooks Javin asks for. Presence must never award XP or quest completion (BE-13.3), and learning features must work with presence down.
- [ ] **12.9 Hard guard.** The location flag **cannot be enabled in production** until the review in BE-16.6 is signed in Appendix C. Implement this as a check in code or release procedure, not only a document.

## Tests required
Sharing off or expired returns no location to anyone, including friends; no "everyone" audience accepted; auto-expiry; no position history table exists; non-members get nothing; analytics events contain no coordinates; the flag guard blocks enabling without sign-off; no payment code paths exist.

## Acceptance (SRS)
A student can find a verified campus business, view its listing and make an enquiry, and no payment can be taken anywhere. With sharing off, no endpoint returns the student's location.

## Do not
Store location history; add an "everyone" audience; add any transaction, escrow or wallet feature; enable either flag.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-12-business-and-location.md. Start with Part A planning, and produce only the location design note (12.4). Wait for approval before any location code.
