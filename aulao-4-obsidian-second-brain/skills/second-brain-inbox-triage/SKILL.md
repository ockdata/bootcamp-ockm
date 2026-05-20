---
name: second-brain-inbox-triage
description: Use when the user wants to sort new material in this vault, especially items in 0 - Staging or 6 - Notes, and needs help deciding what should become a stakeholder, project, knowledge, meeting, or reference note.
---

# Second Brain Inbox Triage

Use this skill when the vault has new raw material that needs to be organized.

## Goal

Reduce clutter in `0 - Staging/` and `6 - Notes/` by promoting durable content into the right folders.

## Workflow

1. Read `index.md` and `readme.md` first.
2. Inspect `0 - Staging/` and `6 - Notes/`.
3. Classify each item by intent:
   - relationship context -> `1 - Stakeholders/`
   - execution context -> `2 - Projects/`
   - reusable insight -> `3 - Knowledge/`
   - agenda, decision, or discussion record -> `4 - Meetings/`
   - processed supporting evidence -> `5 - References/`
   - still temporary or unclear -> keep in place
4. Create or update the destination notes.
5. Add `[[wikilinks]]` between the promoted note and any related stakeholder, project, meeting, or reference.
6. Update `index.md` only when a new durable note materially improves navigation.

## Decision Rules

- Do not leave a note in `6 - Notes/` if it has become clearly durable.
- Do not keep processed source material in `0 - Staging/` once its destination is obvious.
- Prefer one concise permanent note over several overlapping scratch notes.
- If classification is uncertain, state the ambiguity instead of forcing a category.

## Output Style

When reporting back, state:

- what was promoted
- what stayed in staging or notes
- which new links were created
