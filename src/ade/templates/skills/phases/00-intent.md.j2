# Phase 0 — Intent Extraction

## Purpose

Extract structured requirements from a task description, feature spec, bug report, or
conversation. The intent document is the single source of truth for what "done" looks like
and gates every subsequent phase.

## Input Sources

| Source | How to handle |
|--------|--------------|
| Feature spec file | Parse directly — sections map 1:1 to intent fields |
| One-line description | Ask clarifying questions before proceeding |
| Bug report / issue | Extract reproduction steps as implicit acceptance criteria |
| Conversation context | Summarize the agreed-upon scope; confirm with user |

## Output Format

Save to `.ade/tasks/<task-id>/intent.md` with this exact structure:

```markdown
# Intent: <task-id>

**Type:** feature | bugfix | refactor
**Goal:** One-sentence summary of what this change accomplishes.

## Acceptance Criteria
- [ ] Criterion 1 — specific, testable outcome
- [ ] Criterion 2 — specific, testable outcome
- [ ] Criterion 3 — specific, testable outcome

## Affected Areas
- packages/shared: <what changes>
- packages/backend: <what changes>
- packages/frontend: <what changes>

## Estimated Scope
- **Size:** S (< 3 files) | M (3–10 files) | L (> 10 files)
- **Rationale:** Brief explanation of scope estimate
```

## Field Guidelines

### Type
- **feature** — new user-facing capability or entirely new internal system
- **bugfix** — correcting behavior that deviates from existing intent
- **refactor** — restructuring without behavior change (no new tests needed beyond existing)

### Goal
One sentence, imperative mood. Good: "Add CSV export to the nutrition daily endpoint."
Bad: "We need to maybe look into adding some kind of export functionality."

### Acceptance Criteria
Each criterion must be independently verifiable. Use this test: could a reviewer look at
the running system and confirm yes/no whether this criterion is met?

Bad: "The UI looks good." (subjective)
Good: "The nutrition table renders rows for each day in the selected date range." (verifiable)

### Affected Areas
List every package that will have file changes. This drives the build order in later phases
and helps scope the research phase. If unsure, list as "possibly affected" and confirm
during research.

### Estimated Scope
Be honest. Underestimating scope leads to drift detection triggers later. When in doubt,
round up. A task estimated as S that turns into M is a yellow flag; S turning into L is a
red flag that requires re-scoping.

## Handling Ambiguous Inputs

When the input is vague or incomplete:

1. **Identify gaps** — Which intent fields cannot be filled from the input alone?
2. **Propose defaults** — Suggest reasonable values based on codebase context.
3. **Ask the user** — Present the draft intent with `[NEEDS CLARIFICATION]` markers.
4. **Do NOT proceed** past the user gate with unresolved markers.

Example:
> User says: "Fix the workout page"
>
> Response: "I need more detail to extract intent. What specifically is broken on the
> workout page? Are you seeing an error, incorrect data, or a UI rendering issue?"

## Task ID Convention

Format: `<type>-<short-name>` using kebab-case.
Examples: `feature-csv-export`, `bugfix-workout-null-dates`, `refactor-query-layer`.

The task ID is used for directory names, branch names (`ade/<task-id>`), and worktree
paths — keep it short but descriptive.
