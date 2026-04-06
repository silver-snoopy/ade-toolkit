# Phase 10 — Retrospective

## Purpose

Capture metrics, learnings, and follow-ups from the development cycle. The retrospective
enables continuous improvement of the ADE process itself.

## What to Record in retro.json

Save to: `.ade/tasks/<task-id>/retro.json`

```json
{
  "taskId": "<task-id>",
  "type": "feature | bugfix | refactor",
  "completedAt": "2026-04-06T14:30:00Z",

  "cycleTime": {
    "total": "2h 15m",
    "phases": {
      "intent": "5m",
      "research": "15m",
      "userGate": "10m (waiting)",
      "plan": "10m",
      "designCheck": "8m",
      "implement": "45m",
      "qualityGate": "12m",
      "review": "15m",
      "verify": "10m",
      "docs": "5m",
      "ship": "5m"
    }
  },

  "iterations": {
    "designCheck": 1,
    "codeReviewCycles": 2,
    "qaFixAttempts": 1,
    "verifyRejectCycles": 0,
    "totalIterations": 4
  },

  "circuitBreakers": {
    "triggered": false,
    "details": null
  },

  "scope": {
    "estimated": "M",
    "actual": "M",
    "filesPlanned": 8,
    "filesActual": 9,
    "driftDetected": false
  },

  "qualityGate": {
    "lintErrors": 3,
    "formatIssues": 1,
    "buildErrors": 0,
    "testFailures": 2,
    "allResolved": true
  },

  "review": {
    "highFindings": 1,
    "mediumFindings": 2,
    "lowFindings": 3,
    "allHighMediumResolved": true
  },

  "learnings": [
    "The existing CSV utility in shared package could have been reused — check shared utils first",
    "Fastify reply.header must be set before reply.send for streaming responses"
  ],

  "followUps": [
    "Add rate limiting to export endpoint (LOW finding from review)",
    "Consider pagination for large date ranges"
  ]
}
```

## Fields Explained

### cycleTime
Wall-clock time per phase. Includes waiting time for user gates (marked separately).
Helps identify bottleneck phases.

### iterations
Count of loops within each phase. Lower is better.
- **designCheck** — how many stub revision rounds (max 2)
- **codeReviewCycles** — how many code-fix-review loops (max 3)
- **qaFixAttempts** — how many quality gate fix attempts (max 3)
- **verifyRejectCycles** — how many verify-fail-fix loops (max 2)

### circuitBreakers
Whether any iteration limit was hit and required user escalation.

### scope
Compare planned vs actual to calibrate future estimates.

### learnings
Concrete, actionable insights. Not "it went well" but "the mock setup pattern for
Fastify routes needs X because of Y."

### followUps
Items that were identified during the cycle but deferred. Each should be actionable
enough to become its own task.

## Worktree Cleanup After Merge

Once the PR is merged:

```bash
# Remove the worktree
git worktree remove .ade/worktrees/<task-id>

# Delete the local branch
git branch -d ade/<task-id>

# The remote branch is deleted automatically if "Delete branch on merge" is enabled,
# otherwise:
git push origin --delete ade/<task-id>
```

## Status File Final Update

Update `.ade/tasks/<task-id>/status.json`:

```json
{
  "taskId": "<task-id>",
  "status": "completed",
  "phase": "retro",
  "branch": "ade/<task-id>",
  "pr": "#123",
  "mergedAt": "2026-04-06T15:00:00Z",
  "completedAt": "2026-04-06T15:05:00Z"
}
```

## Task Directory Structure (Final)

After completion, the task directory should contain:

```
.ade/tasks/<task-id>/
├── intent.md
├── plan.md
├── status.json
├── retro.json
└── verification/
    ├── 01-default-state.png
    ├── 02-after-interaction.png
    ├── verification-summary.md
    └── api-response.json (if applicable)
```

These files are retained for historical reference and process improvement analysis.
The worktree is removed but the task artifacts remain.
