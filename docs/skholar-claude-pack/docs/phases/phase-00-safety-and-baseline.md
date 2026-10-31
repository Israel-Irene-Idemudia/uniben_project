# Phase 0: Safety and baseline

**Release:** pre-R1 | **SRS:** D7, BE-04.2, NFR-SEC1, section 3.3 rules 8 and 9, DATA-18 (inventory) | **Owner:** Israel | **Size:** S | **Depends on:** none

## Goal
Close the live redemption exploit in the code on this branch, make the repo safe to work in, and produce an audit that every later phase relies on. **No new features.**

## Read first
`CLAUDE.md`, `docs/DECISIONS.md` (D-1, D-10).

## Context
The original `rewards.views.RedeemRewardAPI` reads `point_cost` from the request. A negative value adds points and zero gives free airtime. Tests confirmed both. The full price fix (server-owned prices) comes in Phase 3.

## Tasks (one commit each)
- [ ] **0.1 Git state.** Run `git status` and `git log --oneline -10`. Check whether a commit "reject non-positive redemption cost and lock profile row" exists on this branch. Report; do not assume.
- [ ] **0.2 Redeem fix (only if missing).** In `RedeemRewardAPI.post`: catch `TypeError` and `ValueError` on the cost; reject `point_cost <= 0` with 400; load the profile with `select_for_update()` inside the existing `transaction.atomic`; save once. Keep legacy response shapes.
- [ ] **0.3 Regression tests** in `rewards/test_redeem_validation.py`: valid cost works (201, balance reduced); negative rejected, balance unchanged; zero rejected; non-numeric rejected; cost above balance rejected; missing cost uses the default.
- [ ] **0.4 `.env.example` hygiene.** Replace the real RDS hostname, username and database name with generic placeholders. Scan tracked files for hardcoded secrets (report file names only, never print values).
- [ ] **0.5 Baseline.** Run the full suite. Write `docs/BASELINE.md`: counts, the known failing materials test and its probable cause. Fix it only if trivial, in its own commit.
- [ ] **0.6 `docs/AUDIT.md`** containing: (a) every read and write of `UserProfile.points` (`git grep`); (b) every URL currently exposed with its permission class (legacy compatibility list for D-11); (c) where any avatar data is stored today; (d) model inventory per app, flagging every `on_delete=CASCADE` to the user; (e) how deploy and migrations run (Dockerfile, wsgi hook, `setup_ec2.sh`, any `.github/workflows`); (f) settings risks (default permission class, no throttling, DEBUG logging, insecure `SECRET_KEY` default, keys with no default).

## Tests required
Full suite equals baseline plus the new rewards tests.

## Acceptance
Exploit tests pass. `AUDIT.md` exists and Israel has read it. No behaviour change except the redeem validation.

## Do not
Change production settings, touch existing migrations, run any reset or flush script, or build ledger code yet.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-00-safety-and-baseline.md. Plan tasks 0.1 to 0.6 and wait for my approval before changing anything. Start with 0.1 and report what you find.
