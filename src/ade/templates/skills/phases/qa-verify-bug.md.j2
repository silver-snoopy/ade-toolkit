# QA — Bug Verification Procedure

## Purpose

Reproduce a reported bug against the real running system before any fix is attempted.
Bugs that cannot be reproduced cannot be reliably fixed. This procedure uses Playwright
against the live local stack — NOT mocked or simulated.

## Full Bug Reproduction Procedure

### Step 1: Start Local Stack

```bash
# Database
docker compose up -d

# Build all packages
npm run build -w @vitals/shared
npm run build -w @vitals/backend
npm run build -w @vitals/frontend

# Start backend
npm run dev -w @vitals/backend &

# Start frontend
npm run dev -w @vitals/frontend &

# Wait for services to be ready
curl --retry 10 --retry-delay 2 http://localhost:3001/health
curl --retry 10 --retry-delay 2 http://localhost:3000
```

### Step 2: Reproduce the Bug

Using Playwright against the real system (NOT route interception, NOT mocked data):

```typescript
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: false }); // visible for debugging
const page = await browser.newPage();

// Follow the exact reproduction steps from the bug report
await page.goto('http://localhost:3000/workouts');

// Perform the actions that trigger the bug
// ... (specific to each bug)

// Capture the broken state
await page.screenshot({
  path: '.ade/tasks/<task-id>/verification/before-bug.png',
  fullPage: true,
});

await browser.close();
```

### Step 3: Capture the Broken State

Take a screenshot at the moment the bug manifests. The screenshot should clearly show:
- The incorrect behavior (error message, wrong data, broken layout)
- Enough context to understand what page/feature is affected
- Browser console errors (if relevant, capture via `page.on('console')`)

```typescript
// Capture console errors
const consoleErrors: string[] = [];
page.on('console', (msg) => {
  if (msg.type() === 'error') {
    consoleErrors.push(msg.text());
  }
});

// ... reproduce bug ...

// Save console errors
fs.writeFileSync(
  '.ade/tasks/<task-id>/verification/console-errors.txt',
  consoleErrors.join('\n')
);
```

### Step 4: Document Reproduction Steps

Create `.ade/tasks/<task-id>/verification/reproduction.md`:

```markdown
# Bug Reproduction: <task-id>

## Reported Behavior
[Copy from bug report]

## Environment
- Branch: main (before fix)
- Database: Docker PostgreSQL with seed data
- Backend: localhost:3001
- Frontend: localhost:3000

## Reproduction Steps
1. Navigate to http://localhost:3000/workouts
2. Select date range 2026-01-01 to 2026-01-07
3. Click on "Bench Press" exercise
4. Observe: progress chart shows NaN for sets with null weight

## Expected Behavior
Progress chart should skip or show 0 for sets without weight data.

## Actual Behavior
Chart renders "NaN" labels and the line breaks at null data points.

## Evidence
- Screenshot: `before-bug.png`
- Console errors: `console-errors.txt`

## Reproduced: YES / NO
```

## When to Mark as "Not Reproducible"

A bug is "not reproducible" if after reasonable effort:

1. **Environment matches** — same database state, same browser, same OS
2. **Steps followed exactly** — no deviation from reported reproduction steps
3. **Multiple attempts** — tried at least 3 times
4. **Variations tested** — tried with different data, different browsers

If not reproducible:
- Document what was tried
- Note possible explanations (race condition, data-dependent, environment-specific)
- Ask the reporter for more detail or a screen recording
- Do NOT close the bug without user approval

## After Reproduction: Fix and Re-verify

1. Implement the fix in the worktree
2. Rebuild affected packages
3. Restart services
4. Re-run the exact same reproduction steps
5. Capture "after" screenshot: `after-fix.png`
6. Verify the fix doesn't break related functionality

## At User Gate: Regression Test Decision

After reproducing the bug and before implementing the fix, ask the user:

> "Bug confirmed and reproduced. Should I add a permanent regression test to prevent
> this bug from recurring? This would be:
> - Unit test: [describe what it would test]
> - E2E test: [describe what it would test]
> - Both
> - Neither (fix only)"

The user's answer determines the test strategy in the plan phase.

## Evidence Required for Bug PRs

Bug fix PRs must include:
- `before-bug.png` — the broken state
- `after-fix.png` — the fixed state
- `reproduction.md` — how to reproduce
- Reference to the original bug report/issue

This before/after evidence is non-negotiable for bug fix PRs.
