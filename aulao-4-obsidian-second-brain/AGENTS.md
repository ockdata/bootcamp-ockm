# Obsidian Second Brain Schema

This vault is a markdown second brain maintained collaboratively by a human and an LLM agent.

## Mission

The human captures inputs, runs projects, and asks questions. The agent keeps the vault organized, promotes notes into the right folders, improves links, and prevents structural drift.

## Directory Contract

- `0 - Staging/` is the inbox for raw captures, imports, attachments, and unprocessed material.
- `1 - Stakeholders/` stores durable notes about people, teams, organizations, clients, and partners.
- `2 - Projects/` stores project notes, plans, status, deliverables, and execution context.
- `3 - Knowledge/` stores evergreen knowledge, synthesized insights, frameworks, and concepts.
- `4 - Meetings/` stores agendas, meeting notes, decisions, and follow-up records.
- `5 - References/` stores processed source notes, excerpts, documentation notes, and supporting material.
- `6 - Notes/` stores scratch notes, fleeting ideas, and uncategorized drafts.
- `skills/` stores local agent skills and workflow instructions for maintaining the vault.
- `index.md` remains the root catalog for the vault.
- `readme.md` remains the root usage guide for the vault.

## Required Behaviors

When organizing new material:

1. Read `index.md` first.
2. Check whether the material is still raw, active, or already durable.
3. Place it in the smallest folder that matches its current state.
4. Add `[[wikilinks]]` to related notes when a real connection exists.
5. Promote notes out of `0 - Staging/` and `6 - Notes/` when they become durable.
6. Update `index.md` when a new durable note materially improves navigation.

When answering a question:

1. Read `index.md` first.
2. Read only the most relevant notes.
3. Synthesize the answer with explicit references to the files used.
4. If the answer is durable, save it in the most appropriate folder and link it from `index.md` if needed.

When cleaning the vault:

1. Look for orphan notes.
2. Look for stale or duplicate notes.
3. Look for items stranded in `0 - Staging/` or `6 - Notes/`.
4. Promote reusable knowledge into `3 - Knowledge/`.
5. Archive relationship and execution context into `1 - Stakeholders/`, `2 - Projects/`, `4 - Meetings/`, or `5 - References/`.

## Writing Conventions

- Prefer short, linked markdown pages over large monoliths.
- Use descriptive titles and stable filenames.
- Add frontmatter only when it helps filtering, indexing, or automation.
- Keep project-specific context inside `2 - Projects/`.
- Keep relationship-specific context inside `1 - Stakeholders/`.
- Keep reusable ideas inside `3 - Knowledge/`.
- Keep supporting evidence inside `5 - References/`.
- Mark uncertainty explicitly instead of smoothing over gaps.

## Safety Rules

- Do not fabricate citations, source claims, or meeting outcomes.
- Do not silently merge conflicting claims; note the conflict and preserve both sides.
- Do not leave processed material stranded in `0 - Staging/` if its destination is clear.
- If evidence is insufficient, state the gap and identify the next note or source to create.
