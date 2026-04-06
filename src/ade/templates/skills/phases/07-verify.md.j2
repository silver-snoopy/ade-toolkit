# Phase 7 — Verify

## Purpose

MANDATORY live verification of the implemented feature or fix against the actual running
system. This phase produces evidence that acceptance criteria are met. **NO EXEMPTIONS**
regardless of change type — even "just a refactor" or "only backend" changes must be
verified against the live system.

## Live Verification Procedure

### Step 1: Start Local Environment

```bash
# Start database
docker compose up -d

# Build all packages (in order)
npm run build -w @vitals/shared
npm run build -w @vitals/backend
npm run build -w @vitals/frontend

# Start backend (terminal 1)
npm run dev -w @vitals/backend

# Start frontend (terminal 2)
npm run dev -w @vitals/frontend
```

Verify both services are running:
- Backend: `http://localhost:3001` responds to health check
- Frontend: `http://localhost:3000` loads without errors

### Step 2: Verify Each Acceptance Criterion

For each criterion in the intent document:

1. **Describe the test action** — what you will do
2. **Perform the action** — against the live system
3. **Capture evidence** — screenshot or API response
4. **Record the result** — PASS or FAIL with explanation

### Step 3: Capture Screenshot Evidence

Use Playwright for consistent, reproducible screenshots:

```typescript
// Temporary verification script
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

// Navigate to the relevant page
await page.goto('http://localhost:3000/nutrition');

// Wait for data to load
await page.waitForSelector('[data-testid="nutrition-table"]');

// Capture screenshot
await page.screenshot({
  path: '.ade/tasks/<task-id>/verification/nutrition-page.png',
  fullPage: true,
});

await browser.close();
```

### Step 4: API Verification (for backend changes)

```bash
# Capture request/response evidence
curl -s http://localhost:3001/api/nutrition/daily?startDate=2026-01-01&endDate=2026-01-07 \
  -H "x-api-key: $API_KEY" | jq . > .ade/tasks/<task-id>/verification/api-response.json
```

## Screenshot Capture Guidelines

### Key States to Capture
- **Default state** — page loaded with typical data
- **Empty state** — page with no data (if applicable)
- **Error state** — what happens when something goes wrong
- **Loading state** — spinner or skeleton shown during data fetch
- **Interactive state** — after user interaction (button click, form submit)

### Evidence File Naming Convention

```
.ade/tasks/<task-id>/verification/
├── 01-default-state.png
├── 02-after-interaction.png
├── 03-error-state.png
├── 04-api-response.json
└── verification-summary.md
```

Name files with a numeric prefix for ordering and a descriptive suffix.

## Verification Summary

Create `.ade/tasks/<task-id>/verification/verification-summary.md`:

```markdown
# Verification: <task-id>

## Environment
- Date: YYYY-MM-DD
- Branch: ade/<task-id>
- Backend: localhost:3001
- Frontend: localhost:3000
- Database: Docker PostgreSQL

## Acceptance Criteria Results

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Nutrition table renders daily rows | PASS | 01-default-state.png |
| 2 | Export button triggers CSV download | PASS | 02-after-interaction.png |
| 3 | Empty date range shows message | PASS | 03-error-state.png |

## Overall Verdict: PASS / FAIL
```

## Bugfix Verification: Before/After Comparison

For bugfixes, capture evidence of both states:

1. **Before** — checkout the base branch, start the system, capture the bug
2. **After** — checkout the task branch, start the system, capture the fix

```
.ade/tasks/<task-id>/verification/
├── before-bug.png
├── after-fix.png
└── verification-summary.md
```

The before/after comparison is required for PR evidence.

## Failure Handling

If any acceptance criterion fails:

1. Document the failure with evidence
2. Loop back to Review phase (Phase 6)
3. Fix the issue
4. Re-verify ALL criteria (not just the failing one)
5. **Maximum 2 verify-to-review reject cycles.** After 2, escalate to user.

## Cleanup Procedure

After verification is complete:

1. Stop the frontend dev server
2. Stop the backend dev server
3. Optionally stop Docker if not needed: `docker compose down`
4. Delete temporary verification scripts (not the evidence files)
5. Keep all evidence files — they will be referenced in the PR

## NO EXEMPTIONS

Even if the change is:
- "Just a type change" — verify the build and that consumers work
- "Just a refactor" — verify behavior is unchanged
- "Only tests" — verify tests actually run and pass against the system
- "Only documentation" — verify docs render correctly (if applicable)
- "Backend only" — verify API responses are correct via curl or Playwright

Every change can break something. Verify it doesn't.
