# Phase 9: Classrooms and learning rooms

**Release:** R2 (flag off until gate) | **SRS:** BE-10.1 to 10.6, DATA-09 | **Owner:** Israel | **Size:** L | **Depends on:** 5, 8 (and 10 for shared courses)

## Goal
Shared learning without live voice, video or full multiplayer.

## Tasks
- [ ] **9.1 Rooms (BE-10.1, 10.2).** `Classroom` (name, course or objective, privacy: code-only or invite-only) and `ClassroomMember`. Create; join by code or owner invite; owner can remove members, **rotate the code** (old code stops working immediately), and close the room. Store the join code hashed or rotatable.
- [ ] **9.2 Classwork (BE-10.4).** `Assignment` and `Submission`: set by the owner, submitted by members, marked complete by the defined rule.
- [ ] **9.3 Room Past Questions (BE-10.4).** Room-level practice and challenges through the Phase 5 services; individual results preserved.
- [ ] **9.4 Shared courses (BE-10.3).** Sections shared inside a room, each member's own progress, plus an aggregate room view exposing nothing beyond what members consented to share. Depends on Phase 10 models; build the consent model now and wire it after Phase 10.
- [ ] **9.5 Group quests (BE-10.5, Should).** Via the Phase 4 group-quest support; record participation per member.
- [ ] **9.6 Moderation hooks (BE-10.6).** Report a room or member; admin can suspend a room; owner can block a user from rejoining. Notifications for classroom activity (Phase 6 triggers).

## Tests required
Code-only room admits only code holders; rotating the code kills the old one at once; non-members cannot read room data (IDOR); aggregate view leaks no private detail; blocked and suspended users cannot join; assignment submission rules.

## Acceptance (SRS)
Room members can complete the same course section and a group Past Questions challenge with individual results preserved.

## Do not
Build live voice, video or real-time multiplayer; enable the flag.

## Start prompt
> Read CLAUDE.md and docs/phases/phase-09-classrooms.md. Plan tasks 9.1 to 9.6, noting which depend on Phase 10. Wait for approval.
