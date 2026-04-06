# Future Hardening — File Safety

## Pre-phase snapshot + restore on truncation

**Status:** Planned (not yet implemented)
**Priority:** Medium — safety net for when edit mode is misused
**Depends on:** Edit mode (implemented)

### Problem

Even with `mode='edit'` available, a sub-agent might still use `mode='write'`
on an existing file, destroying its content. The task description instructs
against this, but local LLMs don't always follow instructions.

### Proposed solution

1. **Snapshot at phase start**: Before `code` or `fix` phases, the runner
   snapshots all files that exist in the worktree and appear in `plan_files`:

   ```python
   snapshots = {}
   for f in plan_files:
       target = worktree_path / f
       if target.exists():
           snapshots[f] = target.read_text(encoding="utf-8")
   ```

   Store in `.ade/tasks/<id>/.snapshots/` as flat files.

2. **Detect truncation after phase**: After `crew.kickoff()`, compare each
   modified file against its snapshot. If a file lost more than 50% of its
   lines, flag it as truncated:

   ```python
   for f, original in snapshots.items():
       current = (worktree_path / f).read_text()
       if len(current.splitlines()) < len(original.splitlines()) * 0.5:
           # Restore from snapshot
           (worktree_path / f).write_text(original)
           progress.log(status=f"RESTORED {f} — agent truncated it")
   ```

3. **Return EXIT_PARTIAL** if any files were restored, so the orchestrator
   knows the phase didn't fully succeed.

### Why not implement now

The edit mode fix addresses the root cause. The snapshot approach is a
defense-in-depth layer for when agents ignore tool guidance. It adds
complexity (snapshot storage, comparison logic, restoration) that isn't
needed until we observe the edit-mode guidance being violated in practice.

### Implementation estimate

~100 LOC in `runner.py` + 3-4 tests. Could be done in a single session.
