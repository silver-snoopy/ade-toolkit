# Phase 8 — Documentation

## Purpose

Update all project documentation affected by the change. Documentation is not optional —
it is a gate before shipping. Only update docs that are actually affected; do not make
gratuitous changes.

## Product Capabilities (`docs/product-capabilities.md`)

### When to Update
- New user-facing feature
- Changed behavior of existing feature
- Removed capability

### Format

Each capability uses a use-case ID:

```markdown
### UC-NUT-05: Export Daily Nutrition as CSV

**User Story:** As a user, I want to export my daily nutrition data as a CSV file so I can
analyze it in a spreadsheet.

**Behavior:**
- Navigate to Nutrition page
- Click "Export CSV" button in the toolbar
- Browser downloads a CSV file with columns: date, calories, protein, carbs, fat
- Date range matches the currently selected filter

**E2E Coverage:** `e2e/nutrition-export.spec.ts`
```

### Use-Case ID Convention

Format: `UC-<AREA>-<NN>`

| Area code | Domain |
|-----------|--------|
| NUT | Nutrition |
| WRK | Workouts |
| RPT | Reports |
| DSH | Dashboard |
| UPL | Upload |
| SET | Settings |
| AI | AI/Intelligence |

Number sequentially within each area. Check existing IDs before assigning to avoid
duplicates.

## CLAUDE.md

### When to Update
- New package added to the monorepo
- New convention established (naming pattern, file structure)
- New development command (build, test, lint)
- New environment variable required
- New external dependency with usage notes
- Changed project structure

### What NOT to Update
- Do not add task-specific notes (those go in memory or task docs)
- Do not document temporary workarounds
- Do not add TODO items

## Architecture Docs (`docs/architecture.md`)

### When to Update
- New API route added
- New database table or migration
- New service or provider
- Changed data flow between components
- New external integration

### What to Include
- Route path, method, auth requirement
- Database table name, key columns, relationships
- Service class/function name, responsibility
- Data flow diagrams (text-based, using ASCII or Mermaid)

## API Documentation

### When to Update
- New endpoint
- Changed request/response shape
- Changed authentication requirements
- Deprecated endpoint

### Format
```markdown
### GET /api/nutrition/export

**Auth:** API key required (`x-api-key` header)

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| startDate | string (YYYY-MM-DD) | yes | Start of date range |
| endDate | string (YYYY-MM-DD) | yes | End of date range |
| format | string | no | Export format: `csv` (default) or `json` |

**Response:** File download (CSV or JSON)

**Error Responses:**
- 400: Invalid date range
- 401: Missing or invalid API key
```

## What NOT to Update for Refactors

If the change is a pure refactor (no behavior change):

- Do NOT update product capabilities (behavior hasn't changed)
- Do NOT update API docs (endpoints haven't changed)
- DO update architecture docs if internal structure changed significantly
- DO update CLAUDE.md if the refactor established a new pattern or convention

## Documentation Checklist

Before proceeding to Phase 9:

- [ ] Product capabilities updated (if user-facing change)
- [ ] CLAUDE.md updated (if new conventions or structure)
- [ ] Architecture docs updated (if new routes, tables, or services)
- [ ] API docs updated (if new or changed endpoints)
- [ ] All use-case IDs are unique and sequential
- [ ] E2E coverage references point to actual test files
