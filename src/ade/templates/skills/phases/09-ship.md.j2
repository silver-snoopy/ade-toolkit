# Phase 9 — Commit & PR

## Purpose

Create a clean commit history and open a pull request with full context, verification
evidence, and test plan.

## What NOT to Commit

Never commit these files:
- `.env` — environment variables with secrets
- `credentials.json` — API credentials
- `node_modules/` — package dependencies
- `.ade/worktrees/` — worktree working directories
- `*.local` — local configuration overrides
- Any file containing API keys, tokens, or passwords

If any of these are staged, unstage them before committing:
```bash
git reset HEAD .env credentials.json
```

## Conventional Commit Format

```
<type>: <description>

<body>

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Type Prefixes
| Type | When to use |
|------|------------|
| `feat` | New user-facing feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `test` | Adding or updating tests only |
| `docs` | Documentation only |
| `chore` | Build, CI, tooling changes |
| `perf` | Performance improvement |

### Examples

```
feat: add CSV export to nutrition daily endpoint

Adds GET /api/nutrition/export with CSV and JSON format support.
Includes date range validation and streaming response for large exports.

Closes #42
```

```
fix: handle null dates in workout session grouping

Workout sets with null performed_at were crashing the session grouper.
Now filters them out and logs a warning.

Fixes #87
```

### Rules
- First line: imperative mood, max 72 characters
- Blank line between subject and body
- Body: explain WHY, not WHAT (the diff shows what)
- Reference issue numbers when applicable

## Staging and Committing

```bash
# Stage specific files (preferred over git add -A)
git add packages/shared/src/types/export.ts
git add packages/backend/src/routes/nutrition.ts
git add packages/backend/src/db/queries/measurements.ts
# ... etc

# Verify what's staged
git diff --staged --stat

# Commit
git commit -m "feat: add CSV export to nutrition daily endpoint

Adds GET /api/nutrition/export with CSV and JSON format support.
Includes date range validation and streaming response for large exports.

Closes #42

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Push to Remote

```bash
git push -u origin ade/<task-id>
```

## Pull Request

### PR Title
- Short, under 70 characters
- Same format as commit subject line
- Example: `feat: add CSV export to nutrition daily endpoint`

### PR Body Template

```markdown
## Summary
- Add CSV/JSON export endpoint for daily nutrition data
- Includes date range validation and empty-data handling
- New E2E test covers export flow

## Use Cases
- UC-NUT-05: Export Daily Nutrition as CSV

## Visual Verification
<!-- Screenshots from Phase 7 -->
![Default state](./verification/01-default-state.png)
![After export](./verification/02-after-interaction.png)

## Test Plan
- [ ] Unit tests: `npm test -w @vitals/backend` (query + route tests)
- [ ] E2E tests: `npm run test:e2e` (nutrition-export.spec.ts)
- [ ] Manual: Navigate to Nutrition → Export → verify file downloads

## Changes
- `packages/shared/src/types/export.ts` — new ExportFormat type
- `packages/backend/src/db/queries/measurements.ts` — CSV query function
- `packages/backend/src/routes/nutrition.ts` — export route
- `packages/frontend/src/pages/Nutrition.tsx` — export button
- `e2e/nutrition-export.spec.ts` — E2E test
```

### Creating the PR

```bash
gh pr create \
  --title "feat: add CSV export to nutrition daily endpoint" \
  --body "$(cat <<'EOF'
## Summary
- Add CSV/JSON export endpoint for daily nutrition data
- Includes date range validation and empty-data handling

## Test Plan
- [ ] Unit tests pass
- [ ] E2E tests pass

🤖 Generated with Claude Code
EOF
)"
```

### Uploading Screenshots to PR

```bash
# Upload verification screenshots as PR comments
gh pr comment <PR_NUMBER> --body "## Visual Verification

### Default State
![default](./verification/01-default-state.png)

### After Export
![export](./verification/02-after-interaction.png)"
```

For bugfixes, include before/after:
```bash
gh pr comment <PR_NUMBER> --body "## Before/After

### Before (bug)
![before](./verification/before-bug.png)

### After (fix)
![after](./verification/after-fix.png)"
```

## Merge Gate

After creating the PR, present it to the user for review and merge decision.
Do NOT merge automatically. The user decides when and how to merge.

Provide:
- PR URL
- Summary of changes
- Test results
- Any known limitations or follow-up items
