# Skholar Claude Code pack

Unzip into the **root of your uniben_project folder** so you get:

```
CLAUDE.md
.claude/settings.json
docs/SRS.md  PHASES.md  PROGRESS.md  DECISIONS.md  API_CONVENTIONS.md
docs/phases/phase-00 ... phase-13
```

Then, on branch `skholar-world-dev`:

1. `claude` (start Claude Code in the project folder).
2. Paste the **Start prompt** at the bottom of `docs/phases/phase-00-safety-and-baseline.md`.
3. Review each plan and diff before approving. Push yourself, after review.

`.claude/settings.json` asks before every `git push`, blocks force-pushes and pushes to `main`, blocks reading `.env`, and blocks the destructive reset scripts. Check it with `/permissions` inside Claude Code because rule syntax can change.
