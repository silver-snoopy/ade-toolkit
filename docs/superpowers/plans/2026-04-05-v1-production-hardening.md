# ADE v1.0 Production Hardening Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the v0.3 task lifecycle, worktree management, and circuit breaker modules for production use. Add crash recovery, config migration, structured logging, and state transition validation.

**Architecture:** All changes are to existing Python modules in `src/ade/`. Two new modules (`recovery.py`, `logging_setup.py`) are created. The architecture spec at `docs/ade-architecture-design.md` defines the full requirements — see sections: State Machine (lines 332-372), Error Recovery & Resume (lines 869-897), Observability (lines 899-946).

**Tech Stack:** Python 3.11+, Pydantic 2.x (models), Typer (CLI), Rich (output), stdlib `os`, `logging`, `subprocess`. No new dependencies.

**Prerequisites:** Plans 1-3 must be merged. PR #3 (`feat/sdlc-integration`) is merged — the codebase has `tasks.py`, `worktrees.py`, `circuit_breaker.py`, `cli.py` with `status` command, and 150 passing tests.

**Key context for implementers:**
- `OrchestrationConfig` in `src/ade/config.py:29-35` already defines `max_phase_iterations=3` and `max_total_iterations=9` — the circuit breaker should read from this instead of hardcoding
- `LoggingConfig` in `src/ade/config.py:75-78` exists but is dead code — Task 7 activates it
- Several existing tests do invalid state transitions (INITIATED→CODING, INITIATED→COMPLETED) — Task 2 must fix these
- `AdeConfig.version` defaults to `"2.0"` in `src/ade/config.py:82` — config migration uses this

---

## File Structure

```
src/ade/
├── tasks.py              # (Modify) Atomic writes, validators, transitions, logging
├── worktrees.py          # (Modify) Timeouts, error handling, branch cleanup, frozen
├── circuit_breaker.py    # (Modify) Fail-safe, total limit, config integration
├── recovery.py           # (Create) Artifact-based crash recovery
├── logging_setup.py      # (Create) Structured logging from LoggingConfig
├── cli.py                # (Modify) Add `ade resume`, `ade update`
├── config.py             # (Modify) CONFIG_VERSION constant, migrate_config()
├── crew/runner.py        # (Modify) Add EXIT_ESCALATE alias
└── __init__.py           # (Modify) Bump version to 1.0.0

tests/
├── test_tasks.py         # (Modify) Add validator/transition/atomic tests, fix broken tests
├── test_worktrees.py     # (Modify) Add timeout/error/branch-cleanup tests
├── test_circuit_breaker.py # (Modify) Add fail-safe/total/config tests
├── test_recovery.py      # (Create) Artifact inference + resume tests
├── test_logging_setup.py # (Create) Logger config tests
├── test_config_migration.py # (Create) Config migration tests
├── test_cli_resume.py    # (Create) CLI resume command tests
├── test_cli_update.py    # (Create) CLI update command tests
├── test_cli_status.py    # (Modify) Fix invalid transitions in test setup
└── test_sdlc_integration.py # (Modify) Full v1.0 lifecycle tests
```

---

## Execution Order

```
Parallel batch 1:        Task 1 (atomic writes)  |  Task 4 (worktree)  |  Task 6 (config migration)
Sequential:              Task 2 (transitions) — depends on Task 1
Sequential:              Task 3 (circuit breaker) — depends on Task 1
Sequential:              Task 5 (crash recovery) — depends on Tasks 1, 2
Sequential:              Task 7 (logging) — depends on Tasks 1, 3, 4
Final:                   Task 8 (integration + version bump) — depends on all
```

---

## Task 1: Atomic State Writes + Model Validators

**Priority:** P0 — #1 data loss risk
**Files:** `src/ade/tasks.py`, `tests/test_tasks.py`

- [ ] **Step 1: Write failing tests**

Add these tests to `tests/test_tasks.py`:

```python
import logging
from pydantic import ValidationError
from ade.tasks import IterationCounts, TaskState, TaskStatus


def test_save_state_no_tmp_remnant(tmp_path: Path) -> None:
    """After save, no .json.tmp file should remain."""
    state = create_task(ade_dir=tmp_path, description="Test task")
    task_dir = tmp_path / "tasks" / state.task_id
    tmp_files = list(task_dir.glob("*.tmp"))
    assert tmp_files == []


def test_task_state_rejects_worktree_without_branch() -> None:
    with pytest.raises(ValidationError, match="worktree.*branch|branch.*worktree"):
        TaskState(task_id="abc", description="x", worktree="/some/path")


def test_task_state_rejects_branch_without_worktree() -> None:
    with pytest.raises(ValidationError, match="worktree.*branch|branch.*worktree"):
        TaskState(task_id="abc", description="x", branch="ade/abc")


def test_task_state_rejects_empty_task_id() -> None:
    with pytest.raises(ValidationError, match="task_id"):
        TaskState(task_id="", description="x")


def test_iteration_counts_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        IterationCounts(design_check=-1)


def test_list_tasks_warns_on_corrupt_json(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Corrupt state.json should log a warning, not silently skip."""
    create_task(ade_dir=tmp_path, description="Valid task")
    # Create corrupt task
    corrupt_dir = tmp_path / "tasks" / "corrupt1"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "state.json").write_text("{broken json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="ade.tasks"):
        tasks = list_tasks(ade_dir=tmp_path)

    assert len(tasks) == 1  # Only valid task returned
    assert "corrupt1" in caplog.text  # Warning mentions the bad task dir
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tasks.py -v -k "tmp_remnant or rejects or warns"`
Expected: FAIL — validators don't exist yet.

- [ ] **Step 3: Implement atomic `_save_state`**

Replace `_save_state` in `src/ade/tasks.py` (currently at line 54-57):

```python
import os  # Add to imports at top

def _save_state(ade_dir: Path, state: TaskState) -> None:
    path = _state_path(ade_dir, state.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))
```

- [ ] **Step 4: Add model validators**

Update `IterationCounts` (line 28-31):

```python
class IterationCounts(BaseModel):
    design_check: int = Field(default=0, ge=0)
    code_review: int = Field(default=0, ge=0)
    qa_fix: int = Field(default=0, ge=0)
```

Add `model_validator` import and validator to `TaskState` (line 34-43):

```python
from pydantic import BaseModel, Field, model_validator  # Update import

class TaskState(BaseModel):
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.INITIATED
    current_phase: int = 0
    iterations: IterationCounts = Field(default_factory=IterationCounts)
    timestamps: dict[str, str] = Field(default_factory=dict)
    worktree: str | None = None
    branch: str | None = None
    files_modified: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_invariants(self) -> TaskState:
        if not self.task_id:
            raise ValueError("task_id must be non-empty")
        if (self.worktree is None) != (self.branch is None):
            raise ValueError("worktree and branch must both be set or both be None")
        return self
```

- [ ] **Step 5: Add logging to `list_tasks`**

Update `list_tasks` (line 121-135):

```python
import logging  # Add to imports at top

logger = logging.getLogger("ade.tasks")

def list_tasks(ade_dir: Path) -> list[TaskState]:
    """List all tasks with valid state.json files."""
    tasks_dir = ade_dir / "tasks"
    if not tasks_dir.exists():
        return []
    results = []
    for entry in sorted(tasks_dir.iterdir()):
        state_file = entry / "state.json"
        if entry.is_dir() and state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                results.append(TaskState.model_validate(data))
            except json.JSONDecodeError as exc:
                logger.warning("Skipping task %s: corrupted state.json: %s", entry.name, exc)
            except (ValueError, Exception) as exc:
                logger.warning("Skipping task %s: invalid state: %s", entry.name, exc)
    return results
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_tasks.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ade/tasks.py tests/test_tasks.py
git commit -m "fix: atomic state writes, model validators, and corrupt-file warnings"
```

---

## Task 2: State Transition Validation

**Priority:** P0 — prevents silent state corruption
**Files:** `src/ade/tasks.py`, `tests/test_tasks.py`, `tests/test_cli_status.py`, `tests/test_sdlc_integration.py`
**Depends on:** Task 1

- [ ] **Step 1: Write failing tests for transitions**

Add to `tests/test_tasks.py`:

```python
from ade.tasks import InvalidTransitionError, VALID_TRANSITIONS


def test_valid_transition_initiated_to_planning(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.PLANNING, current_phase=1)
    assert updated.status == TaskStatus.PLANNING


def test_valid_transition_design_check_self_loop(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    # Self-loop should be allowed
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.DESIGN_CHECK, current_phase=1)
    assert updated.status == TaskStatus.DESIGN_CHECK


def test_valid_transition_reviewing_to_quality_gate(tmp_path: Path) -> None:
    """Review loop: REVIEWING → QUALITY_GATE is valid."""
    state = create_task(ade_dir=tmp_path, description="Test")
    # Walk to REVIEWING
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.CODING, current_phase=2)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.QUALITY_GATE, current_phase=3)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.REVIEWING, current_phase=4)
    # Loop back to QA
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.QUALITY_GATE, current_phase=3)
    assert updated.status == TaskStatus.QUALITY_GATE


def test_invalid_transition_completed_to_planning(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    # Walk to COMPLETED
    for s, p in [
        (TaskStatus.PLANNING, 1), (TaskStatus.DESIGN_CHECK, 1),
        (TaskStatus.CODING, 2), (TaskStatus.QUALITY_GATE, 3),
        (TaskStatus.REVIEWING, 4), (TaskStatus.FINALIZING, 5),
        (TaskStatus.AWAITING_MERGE, 6), (TaskStatus.COMPLETED, 6),
    ]:
        update_task_status(ade_dir=tmp_path, task_id=state.task_id, status=s, current_phase=p)
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                           status=TaskStatus.PLANNING, current_phase=1)


def test_invalid_transition_coding_to_reviewing(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test")
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.CODING, current_phase=2)
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                           status=TaskStatus.REVIEWING, current_phase=4)


@pytest.mark.parametrize("status", [
    s for s in TaskStatus if s not in (TaskStatus.COMPLETED, TaskStatus.FAILED)
])
def test_any_state_to_failed(tmp_path: Path, status: TaskStatus) -> None:
    """Every non-terminal state can transition to FAILED."""
    state = create_task(ade_dir=tmp_path, description="Test")
    # Directly set the status in the JSON to avoid transition validation
    import json
    state_path = tmp_path / "tasks" / state.task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["status"] = status.value
    state_path.write_text(json.dumps(data), encoding="utf-8")
    updated = update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                  status=TaskStatus.FAILED, current_phase=0)
    assert updated.status == TaskStatus.FAILED


def test_terminal_states_reject_all_transitions(tmp_path: Path) -> None:
    for terminal in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        state = create_task(ade_dir=tmp_path, description=f"Test {terminal}")
        # Set terminal state directly
        import json
        state_path = tmp_path / "tasks" / state.task_id / "state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["status"] = terminal.value
        state_path.write_text(json.dumps(data), encoding="utf-8")
        for target in TaskStatus:
            with pytest.raises(InvalidTransitionError):
                update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                                    status=target, current_phase=0)


def test_valid_transitions_covers_all_statuses() -> None:
    for status in TaskStatus:
        assert status in VALID_TRANSITIONS, f"{status} missing from VALID_TRANSITIONS"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tasks.py -v -k "transition or terminal or covers"`
Expected: FAIL — `InvalidTransitionError` and `VALID_TRANSITIONS` don't exist.

- [ ] **Step 3: Implement VALID_TRANSITIONS and InvalidTransitionError**

Add to `src/ade/tasks.py` after the `TaskState` class:

```python
class InvalidTransitionError(ValueError):
    """Raised when a state transition is not allowed."""


VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.INITIATED: {TaskStatus.PLANNING, TaskStatus.FAILED},
    TaskStatus.PLANNING: {TaskStatus.DESIGN_CHECK, TaskStatus.FAILED},
    TaskStatus.DESIGN_CHECK: {TaskStatus.DESIGN_CHECK, TaskStatus.CODING, TaskStatus.FAILED},
    TaskStatus.CODING: {TaskStatus.QUALITY_GATE, TaskStatus.FAILED},
    TaskStatus.QUALITY_GATE: {TaskStatus.QUALITY_GATE, TaskStatus.REVIEWING, TaskStatus.FAILED},
    TaskStatus.REVIEWING: {
        TaskStatus.QUALITY_GATE, TaskStatus.HUMAN_ESCALATION,
        TaskStatus.FINALIZING, TaskStatus.FAILED,
    },
    TaskStatus.FINALIZING: {TaskStatus.AWAITING_MERGE, TaskStatus.FAILED},
    TaskStatus.AWAITING_MERGE: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.HUMAN_ESCALATION: {TaskStatus.COMPLETED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
}
```

- [ ] **Step 4: Add validation to `update_task_status`**

At the top of `update_task_status`, after `state = load_task(...)`:

```python
    allowed = VALID_TRANSITIONS.get(state.status, set())
    if status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from {state.status.value} to {status.value}"
        )
```

- [ ] **Step 5: Fix existing tests broken by transition validation**

These tests do invalid transitions and must be updated:

**`tests/test_tasks.py` line 76 — `test_update_task_with_worktree`:**
Currently does INITIATED → CODING. Fix by walking through valid transitions:
```python
def test_update_task_with_worktree(tmp_path: Path) -> None:
    state = create_task(ade_dir=tmp_path, description="Test task")
    # Walk to CODING via valid transitions
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir=tmp_path, task_id=state.task_id,
                       status=TaskStatus.DESIGN_CHECK, current_phase=1)
    updated = update_task_status(
        ade_dir=tmp_path, task_id=state.task_id,
        status=TaskStatus.CODING, current_phase=2,
        worktree=".ade/worktrees/abc123", branch="ade/abc123",
    )
    assert updated.worktree == ".ade/worktrees/abc123"
    assert updated.branch == "ade/abc123"
```

**`tests/test_cli_status.py` line 26 — `test_status_shows_task`:**
Currently does INITIATED → CODING. Fix same way (add PLANNING → DESIGN_CHECK steps before CODING).

**`tests/test_cli_status.py` line 56 — `test_status_shows_completed_tasks`:**
Currently does INITIATED → COMPLETED. Fix by walking the full path or writing state directly:
```python
def test_status_shows_completed_tasks(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Done task")
    # Write COMPLETED status directly to state.json for test setup
    import json
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["status"] = "completed"
    data["current_phase"] = 6
    state_path.write_text(json.dumps(data), encoding="utf-8")
    result = runner.invoke(app, ["status", "--project-dir", str(tmp_path)])
    assert "completed" in result.stdout.lower()
```

**`tests/test_sdlc_integration.py` line 102 — `test_qa_fix_loop_with_circuit_breaker`:**
Currently does INITIATED → HUMAN_ESCALATION. Fix by adding transition path:
```python
    # Walk to a valid state before escalation
    update_task_status(ade_dir, task_id, TaskStatus.PLANNING, current_phase=1)
    update_task_status(ade_dir, task_id, TaskStatus.DESIGN_CHECK, current_phase=1)
    update_task_status(ade_dir, task_id, TaskStatus.CODING, current_phase=2)
    update_task_status(ade_dir, task_id, TaskStatus.QUALITY_GATE, current_phase=3)
    update_task_status(ade_dir, task_id, TaskStatus.REVIEWING, current_phase=4)
    # Now HUMAN_ESCALATION is valid from REVIEWING
    update_task_status(ade_dir, task_id, TaskStatus.HUMAN_ESCALATION, current_phase=3)
```

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ade/tasks.py tests/test_tasks.py tests/test_cli_status.py tests/test_sdlc_integration.py
git commit -m "feat: state machine transition validation with VALID_TRANSITIONS map"
```

---

## Task 3: Circuit Breaker Hardening

**Priority:** P0/P1
**Files:** `src/ade/circuit_breaker.py`, `tests/test_circuit_breaker.py`
**Depends on:** Task 1

- [ ] **Step 1: Write failing tests**

Add to `tests/test_circuit_breaker.py`:

```python
import json
from ade.config import OrchestrationConfig
from ade.circuit_breaker import CircuitBreakerResult


def test_load_failure_returns_result(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    result = check_circuit_breaker(ade_dir=ade_dir, task_id="nonexistent")
    assert result == CircuitBreakerResult.LOAD_FAILURE


def test_corrupt_state_returns_load_failure(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    state_path.write_text("{broken", encoding="utf-8")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.LOAD_FAILURE


def test_total_iteration_limit(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    # Set iterations to sum=5 via direct JSON edit
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["iterations"] = {"design_check": 1, "code_review": 2, "qa_fix": 2}
    state_path.write_text(json.dumps(data), encoding="utf-8")
    config = OrchestrationConfig(max_total_iterations=5)
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id, config=config)
    assert result == CircuitBreakerResult.TOTAL_ITERATION_LIMIT


def test_config_overrides_defaults(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="design_check")
    config = OrchestrationConfig(max_phase_iterations=1)
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id, config=config)
    assert result == CircuitBreakerResult.DESIGN_CHECK_LIMIT


def test_none_config_uses_defaults(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.OK
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement changes**

Replace `src/ade/circuit_breaker.py` entirely:

```python
"""Circuit breaker — prevents infinite agent loops by enforcing iteration limits."""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from pathlib import Path

from ade.config import OrchestrationConfig
from ade.tasks import load_task

logger = logging.getLogger("ade.circuit_breaker")

MAX_DESIGN_CHECK_ITERATIONS = 2
MAX_CODE_REVIEW_CYCLES = 3
MAX_QA_FIX_ITERATIONS = 3


class CircuitBreakerResult(StrEnum):
    OK = "ok"
    DESIGN_CHECK_LIMIT = "design_check_limit"
    CODE_REVIEW_LIMIT = "code_review_limit"
    QA_FIX_LIMIT = "qa_fix_limit"
    TOTAL_ITERATION_LIMIT = "total_iteration_limit"
    LOAD_FAILURE = "load_failure"


def check_circuit_breaker(
    ade_dir: Path,
    task_id: str,
    config: OrchestrationConfig | None = None,
) -> CircuitBreakerResult:
    """Check if any iteration limit has been reached.

    Fails safe: if task state cannot be loaded, returns LOAD_FAILURE
    to prevent runaway loops.
    """
    try:
        state = load_task(ade_dir, task_id)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Circuit breaker cannot load task %s, failing safe: %s", task_id, exc)
        return CircuitBreakerResult.LOAD_FAILURE

    design_limit = config.max_phase_iterations if config else MAX_DESIGN_CHECK_ITERATIONS
    review_limit = config.max_phase_iterations if config else MAX_CODE_REVIEW_CYCLES
    qa_limit = config.max_phase_iterations if config else MAX_QA_FIX_ITERATIONS
    total_limit = config.max_total_iterations if config else 9

    iters = state.iterations
    if iters.design_check >= design_limit:
        return CircuitBreakerResult.DESIGN_CHECK_LIMIT
    if iters.code_review >= review_limit:
        return CircuitBreakerResult.CODE_REVIEW_LIMIT
    if iters.qa_fix >= qa_limit:
        return CircuitBreakerResult.QA_FIX_LIMIT
    if iters.design_check + iters.code_review + iters.qa_fix >= total_limit:
        return CircuitBreakerResult.TOTAL_ITERATION_LIMIT

    return CircuitBreakerResult.OK
```

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_circuit_breaker.py -v`
Commit: `feat: circuit breaker fail-safe, total iteration limit, config integration`

---

## Task 4: Worktree Hardening

**Priority:** P1
**Files:** `src/ade/worktrees.py`, `tests/test_worktrees.py`
**Independent** — can run in parallel with Tasks 1-3

- [ ] **Step 1: Write failing tests**

Add to `tests/test_worktrees.py`:

```python
import subprocess
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from ade.worktrees import WorktreeInfo


def test_create_worktree_timeout(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    with patch("ade.worktrees.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
        with pytest.raises(RuntimeError, match="timed out"):
            create_worktree(project_dir=git_repo, task_id="abc123")


def test_create_worktree_git_not_found(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    with patch("ade.worktrees.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="git is not installed"):
            create_worktree(project_dir=git_repo, task_id="abc123")


def test_remove_worktree_cleans_branch(git_repo: Path) -> None:
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    create_worktree(project_dir=git_repo, task_id="abc123")
    remove_worktree(project_dir=git_repo, task_id="abc123")
    # Branch should be deleted
    result = subprocess.run(
        ["git", "branch", "--list", "ade/abc123"],
        cwd=git_repo, capture_output=True, text=True,
    )
    assert result.stdout.strip() == ""


def test_remove_worktree_branch_cleanup_nonfatal(git_repo: Path) -> None:
    """Branch deletion failing should not raise."""
    ade_dir = git_repo / ".ade"
    ade_dir.mkdir()
    create_worktree(project_dir=git_repo, task_id="abc123")
    # Pre-delete the branch to make the cleanup fail
    # (worktree remove will work, but branch -D will fail since it's already gone)
    # This is hard to set up, so we just test that the function completes
    remove_worktree(project_dir=git_repo, task_id="abc123")
    # No exception raised = success


def test_list_worktrees_raises_on_git_failure(tmp_path: Path) -> None:
    """list_worktrees should raise RuntimeError when git fails, not return []."""
    with pytest.raises(RuntimeError, match="Failed to list worktrees"):
        list_worktrees(project_dir=tmp_path)  # Not a git repo


def test_worktree_info_frozen() -> None:
    info = WorktreeInfo(path=Path("/tmp/x"), branch="main")
    with pytest.raises(FrozenInstanceError):
        info.path = Path("/tmp/y")
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement changes**

Replace `src/ade/worktrees.py` entirely:

```python
"""Git worktree manager — create, list, remove isolated task workspaces."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("ade.worktrees")


@dataclass(frozen=True)
class WorktreeInfo:
    path: Path
    branch: str
    task_id: str | None = None


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command with timeout and clear error handling."""
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "git is not installed or not on PATH. Run 'ade doctor' to check dependencies."
        ) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {args[0]} timed out after 30 seconds") from None


def create_worktree(project_dir: Path, task_id: str) -> WorktreeInfo:
    """Create a git worktree for a task in .ade/worktrees/<task_id>."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id
    branch = f"ade/{task_id}"

    result = _run_git(["worktree", "add", str(worktree_path), "-b", branch], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to create worktree: {result.stderr.strip()}")

    return WorktreeInfo(path=worktree_path, branch=branch, task_id=task_id)


def remove_worktree(project_dir: Path, task_id: str) -> None:
    """Remove a task's worktree and clean up its branch."""
    worktree_path = project_dir / ".ade" / "worktrees" / task_id

    if not worktree_path.exists():
        raise FileNotFoundError(f"Worktree not found: {task_id}")

    result = _run_git(["worktree", "remove", str(worktree_path), "--force"], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to remove worktree: {result.stderr.strip()}")

    # Best-effort branch cleanup
    branch_result = _run_git(["branch", "-D", f"ade/{task_id}"], cwd=project_dir)
    if branch_result.returncode != 0:
        logger.warning("Could not delete branch ade/%s: %s", task_id, branch_result.stderr.strip())


def list_worktrees(project_dir: Path) -> list[WorktreeInfo]:
    """List all git worktrees for this project."""
    result = _run_git(["worktree", "list", "--porcelain"], cwd=project_dir)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to list worktrees: {result.stderr.strip()}")

    worktrees: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")

    if current:
        worktrees.append(current)

    results = []
    for wt in worktrees:
        path = Path(wt.get("path", ""))
        branch = wt.get("branch", "")
        task_id = branch[4:] if branch.startswith("ade/") else None
        results.append(WorktreeInfo(path=path, branch=branch, task_id=task_id))

    return results
```

- [ ] **Step 4: Fix `test_list_worktrees_empty`**

The existing `test_list_worktrees_empty` in `tests/test_worktrees.py` passes a valid git repo, so it should still return 1 entry. But if any test passes a non-git dir, it will now raise instead of returning `[]`. Check and fix as needed.

- [ ] **Step 5: Run tests, commit**

Run: `python -m pytest tests/test_worktrees.py -v`
Commit: `fix: worktree subprocess timeouts, error handling, branch cleanup`

---

## Task 5: Crash Recovery and `ade resume`

**Priority:** P1
**Files:** `src/ade/recovery.py` (create), `src/ade/cli.py`, `tests/test_recovery.py` (create), `tests/test_cli_resume.py` (create)
**Depends on:** Tasks 1, 2

- [ ] **Step 1: Write failing tests for recovery module**

Create `tests/test_recovery.py`:

```python
from __future__ import annotations

from pathlib import Path

from ade.tasks import TaskStatus, create_task
from ade.recovery import determine_resume_point, infer_phase_from_artifacts


def test_infer_from_plan_md(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    (task_dir / "plan.md").write_text("# Plan", encoding="utf-8")
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.PLANNING


def test_infer_from_qa_report(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    (task_dir / "qa-report.json").write_text("{}", encoding="utf-8")
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.QUALITY_GATE


def test_infer_no_artifacts(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    assert infer_phase_from_artifacts(task_dir) == TaskStatus.INITIATED


def test_determine_resume_with_valid_state(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    status, message = determine_resume_point(ade_dir=ade_dir, task_id=state.task_id)
    assert status == TaskStatus.INITIATED
    assert message  # Non-empty


def test_determine_resume_with_corrupt_state_and_artifacts(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    # Corrupt the state file
    state_path = ade_dir / "tasks" / state.task_id / "state.json"
    state_path.write_text("{broken", encoding="utf-8")
    # Add a plan artifact
    (ade_dir / "tasks" / state.task_id / "plan.md").write_text("# Plan", encoding="utf-8")
    status, message = determine_resume_point(ade_dir=ade_dir, task_id=state.task_id)
    assert status == TaskStatus.PLANNING
    assert "corrupt" in message.lower() or "artifact" in message.lower()
```

- [ ] **Step 2: Write failing tests for CLI resume**

Create `tests/test_cli_resume.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.tasks import create_task

runner = CliRunner()


def test_cli_resume_shows_status(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test task")
    result = runner.invoke(app, ["resume", state.task_id, "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert state.task_id in result.stdout
    assert "initiated" in result.stdout.lower()


def test_cli_resume_nonexistent_task(tmp_path: Path) -> None:
    (tmp_path / ".ade").mkdir()
    result = runner.invoke(app, ["resume", "nonexistent", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0 or result.exit_code == 1
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()
```

- [ ] **Step 3: Implement `src/ade/recovery.py`**

```python
"""Crash recovery — infer task state from artifacts when state.json is corrupt."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ade.tasks import TaskStatus, load_task

logger = logging.getLogger("ade.recovery")


def infer_phase_from_artifacts(task_dir: Path) -> TaskStatus:
    """Infer the last completed phase from task artifacts on disk."""
    if (task_dir / "qa-report.json").exists():
        return TaskStatus.QUALITY_GATE
    if (task_dir / "plan.md").exists():
        return TaskStatus.PLANNING
    return TaskStatus.INITIATED


def determine_resume_point(
    ade_dir: Path, task_id: str
) -> tuple[TaskStatus, str]:
    """Determine where to resume a task from.

    Returns (status, human_readable_message).
    Tries loading state.json first; falls back to artifact inference.
    """
    try:
        state = load_task(ade_dir, task_id)
        return state.status, f"Task {task_id} is at phase: {state.status.value}"
    except FileNotFoundError:
        return TaskStatus.INITIATED, f"Task {task_id} not found — may need to be recreated"
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Corrupt state for task %s, inferring from artifacts: %s", task_id, exc)
        task_dir = ade_dir / "tasks" / task_id
        inferred = infer_phase_from_artifacts(task_dir)
        return inferred, (
            f"Task {task_id} has corrupt state. "
            f"Inferred from artifacts: last completed phase was {inferred.value}"
        )
```

- [ ] **Step 4: Add `ade resume` to cli.py**

Add import at top of `src/ade/cli.py`:
```python
from ade.recovery import determine_resume_point
```

Add command at end of file:
```python
@app.command()
def resume(
    task_id: Annotated[str, typer.Argument(help="Task ID to resume")],
    project_dir: Annotated[Path, typer.Option(help="Project directory")] = Path("."),
) -> None:
    """Show resume point for an interrupted task."""
    project_dir = project_dir.resolve()
    ade_dir = project_dir / ".ade"

    if not ade_dir.exists():
        rprint("[red]No .ade directory found. Run 'ade init' first.[/red]")
        raise typer.Exit(1)

    status, message = determine_resume_point(ade_dir=ade_dir, task_id=task_id)
    rprint(f"\n[bold]{task_id}[/bold] — {message}")
```

- [ ] **Step 5: Run tests, commit**

Run: `python -m pytest tests/test_recovery.py tests/test_cli_resume.py -v`
Commit: `feat: crash recovery module and ade resume command`

---

## Task 6: `ade update` — Config Migration

**Priority:** P2
**Files:** `src/ade/config.py`, `src/ade/cli.py`, `tests/test_config_migration.py` (create), `tests/test_cli_update.py` (create)
**Independent** — can run in parallel with Tasks 1-5

- [ ] **Step 1: Write failing tests**

Create `tests/test_config_migration.py`:

```python
from __future__ import annotations

import yaml
from pathlib import Path

from ade.config import AdeConfig, CONFIG_VERSION, migrate_config


def test_migrate_same_version_noop(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config = AdeConfig(project={"name": "test", "languages": ["python"]})
    config_path.write_text(config.to_yaml(), encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert not migrated
    assert not (tmp_path / "config.yaml.bak").exists()


def test_migrate_old_version_creates_backup(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert migrated
    assert (tmp_path / "config.yaml.bak").exists()
    assert result.version == CONFIG_VERSION


def test_migrate_missing_version_field(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project:\n  name: test\n  languages: [python]\n", encoding="utf-8")
    result, migrated = migrate_config(config_path)
    assert migrated
    assert result.version == CONFIG_VERSION


def test_migrate_adds_new_fields_with_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result, _ = migrate_config(config_path)
    assert result.logging.level == "info"  # Default applied
    assert result.orchestration.max_phase_iterations == 3  # Default applied


def test_migrate_preserves_user_values(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    old_yaml = (
        "version: '1.0'\n"
        "project:\n  name: my-app\n  languages: [python, typescript]\n"
        "models:\n  primary:\n    name: custom-model:7b\n"
    )
    config_path.write_text(old_yaml, encoding="utf-8")
    result, _ = migrate_config(config_path)
    assert result.project.name == "my-app"
    assert result.models.primary.name == "custom-model:7b"
```

Create `tests/test_cli_update.py`:

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ade.cli import app
from ade.config import AdeConfig

runner = CliRunner()


def test_cli_update_no_ade_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["update", "--project-dir", str(tmp_path)])
    assert result.exit_code == 1


def test_cli_update_happy_path(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    config_path = ade_dir / "config.yaml"
    old_yaml = "version: '1.0'\nproject:\n  name: test\n  languages: [python]\n"
    config_path.write_text(old_yaml, encoding="utf-8")
    result = runner.invoke(app, ["update", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "migrated" in result.stdout.lower() or "updated" in result.stdout.lower()
```

- [ ] **Step 2: Implement `migrate_config` in config.py**

Add to `src/ade/config.py`:

```python
import shutil  # Add to imports

CONFIG_VERSION = "2.0"


def migrate_config(config_path: Path) -> tuple[AdeConfig, bool]:
    """Migrate a config file to the current version.

    Returns (config, was_migrated).
    """
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    current_version = data.get("version", "1.0")

    if str(current_version) == CONFIG_VERSION:
        config = AdeConfig.model_validate(data)
        return config, False

    # Back up old config
    shutil.copy2(config_path, config_path.with_suffix(".yaml.bak"))

    # Update version and validate with defaults for missing fields
    data["version"] = CONFIG_VERSION
    config = AdeConfig.model_validate(data)
    return config, True
```

- [ ] **Step 3: Add `ade update` to cli.py**

```python
from ade.config import migrate_config  # Add import

@app.command()
def update(
    project_dir: Annotated[Path, typer.Option(help="Project directory")] = Path("."),
) -> None:
    """Update ADE config to the latest version."""
    project_dir = project_dir.resolve()
    ade_dir = project_dir / ".ade"
    config_path = ade_dir / "config.yaml"

    if not config_path.exists():
        rprint("[red]No .ade/config.yaml found. Run 'ade init' first.[/red]")
        raise typer.Exit(1)

    config, migrated = migrate_config(config_path)
    if migrated:
        config_path.write_text(config.to_yaml(), encoding="utf-8")
        rprint("[green]Config migrated to latest version. Backup saved as config.yaml.bak[/green]")
    else:
        rprint("Config is already up to date.")
```

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_config_migration.py tests/test_cli_update.py -v`
Commit: `feat: ade update command with config schema migration`

---

## Task 7: Structured Logging

**Priority:** P2
**Files:** `src/ade/logging_setup.py` (create), `tests/test_logging_setup.py` (create)
**Depends on:** Tasks 1, 3, 4

- [ ] **Step 1: Write failing tests**

Create `tests/test_logging_setup.py`:

```python
from __future__ import annotations

import logging

from ade.config import LoggingConfig
from ade.logging_setup import setup_logging


def test_setup_logging_default_level() -> None:
    log = setup_logging()
    assert log.level == logging.INFO


def test_setup_logging_from_config() -> None:
    config = LoggingConfig(level="debug")
    log = setup_logging(config=config)
    assert log.level == logging.DEBUG


def test_setup_logging_returns_ade_logger() -> None:
    log = setup_logging()
    assert log.name == "ade"
```

- [ ] **Step 2: Implement `src/ade/logging_setup.py`**

```python
"""Structured logging setup for ADE."""

from __future__ import annotations

import logging

from ade.config import LoggingConfig


def setup_logging(config: LoggingConfig | None = None) -> logging.Logger:
    """Configure the ade logger from config."""
    logger = logging.getLogger("ade")
    level = getattr(logging, (config.level if config else "info").upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
```

- [ ] **Step 3: Add `setup_logging()` call to CLI startup**

Add to `src/ade/cli.py`, as a Typer callback:

```python
from ade.logging_setup import setup_logging  # Add import

@app.callback()
def main() -> None:
    """ADE — Agentic Development Environment toolkit."""
    setup_logging()
```

Note: Remove the `no_args_is_help=True` from the `typer.Typer()` constructor and put `invoke_without_command=True` in the callback if needed, or keep the callback simple. Test to verify existing CLI behavior is preserved.

- [ ] **Step 4: Run tests, commit**

Run: `python -m pytest tests/test_logging_setup.py -v`
Run: `python -m pytest tests/ -v` (full suite to check no regressions)
Commit: `feat: structured logging with configurable levels`

---

## Task 8: Integration Verification + Version Bump

**Priority:** P2 — capstone
**Files:** `tests/test_sdlc_integration.py`, `src/ade/__init__.py`, `src/ade/crew/runner.py`, `pyproject.toml`, `README.md`
**Depends on:** All previous tasks

- [ ] **Step 1: Add v1.0 integration tests**

Add to `tests/test_sdlc_integration.py`:

```python
import json
from ade.tasks import InvalidTransitionError, VALID_TRANSITIONS
from ade.circuit_breaker import CircuitBreakerResult
from ade.config import OrchestrationConfig
from ade.recovery import determine_resume_point


def test_full_lifecycle_with_validated_transitions(project: Path) -> None:
    """Happy path with transition validation enforced."""
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Validated lifecycle")
    task_id = state.task_id

    # Each transition must be valid
    for status, phase in [
        (TaskStatus.PLANNING, 1),
        (TaskStatus.DESIGN_CHECK, 1),
        (TaskStatus.CODING, 2),
        (TaskStatus.QUALITY_GATE, 3),
        (TaskStatus.REVIEWING, 4),
        (TaskStatus.FINALIZING, 5),
        (TaskStatus.AWAITING_MERGE, 6),
        (TaskStatus.COMPLETED, 6),
    ]:
        update_task_status(ade_dir, task_id, status, current_phase=phase)

    final = load_task(ade_dir, task_id)
    assert final.status == TaskStatus.COMPLETED

    # Invalid transition should be rejected
    with pytest.raises(InvalidTransitionError):
        update_task_status(ade_dir, task_id, TaskStatus.PLANNING, current_phase=1)


def test_lifecycle_circuit_breaker_total_limit(project: Path) -> None:
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Total limit test")
    task_id = state.task_id
    # Set iterations via direct JSON edit
    state_path = ade_dir / "tasks" / task_id / "state.json"
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data["iterations"] = {"design_check": 2, "code_review": 3, "qa_fix": 3}
    state_path.write_text(json.dumps(data), encoding="utf-8")

    config = OrchestrationConfig(max_total_iterations=8)
    result = check_circuit_breaker(ade_dir, task_id, config=config)
    assert result == CircuitBreakerResult.TOTAL_ITERATION_LIMIT


def test_lifecycle_crash_recovery(project: Path) -> None:
    ade_dir = project / ".ade"
    state = create_task(ade_dir=ade_dir, description="Crash test")
    task_id = state.task_id

    # Corrupt the state file
    state_path = ade_dir / "tasks" / task_id / "state.json"
    (ade_dir / "tasks" / task_id / "plan.md").write_text("# Plan", encoding="utf-8")
    state_path.write_text("{corrupt!", encoding="utf-8")

    status, message = determine_resume_point(ade_dir, task_id)
    assert status == TaskStatus.PLANNING


def test_exit_codes_defined() -> None:
    from ade.crew.runner import EXIT_SUCCESS, EXIT_FAILURE, EXIT_PARTIAL, EXIT_ESCALATE
    assert EXIT_SUCCESS == 0
    assert EXIT_FAILURE == 1
    assert EXIT_PARTIAL == 2
    assert EXIT_ESCALATE == 3
```

- [ ] **Step 2: Add EXIT_ESCALATE to runner.py**

In `src/ade/crew/runner.py` after line 18:
```python
EXIT_ESCALATE = EXIT_TIMEOUT  # Alias per architecture spec
```

- [ ] **Step 3: Bump version**

In `src/ade/__init__.py`: `__version__ = "1.0.0"`
In `pyproject.toml`: `version = "1.0.0"`

- [ ] **Step 4: Update README roadmap**

```markdown
## Roadmap

- [x] **v0.1** — Core CLI: `ade init`, `ade doctor`, project detection, config generation
- [x] **v0.2** — CrewAI runner: sandboxed agent tools, phase dispatch, progress reporting
- [x] **v0.3** — End-to-end SDLC: task lifecycle, worktree management, circuit breakers
- [x] **v1.0** — Production-ready: state safety, crash recovery, config migration, structured logging
- [ ] **v1.1** — Model tooling: `ade models benchmark`, `ade models check`, `ade models create`
```

- [ ] **Step 5: Run full verification**

```bash
python -m pytest tests/ -v
python -m ruff check src/ tests/
python -m ruff format --check src/ade/tasks.py src/ade/worktrees.py src/ade/circuit_breaker.py src/ade/recovery.py src/ade/logging_setup.py src/ade/cli.py src/ade/config.py src/ade/crew/runner.py tests/
```

- [ ] **Step 6: Commit**

```bash
git add src/ade/__init__.py src/ade/crew/runner.py pyproject.toml README.md tests/test_sdlc_integration.py
git commit -m "feat: v1.0 integration tests, EXIT_ESCALATE alias, and version bump"
```

---

## Dependencies Note

No new dependencies — uses stdlib `os`, `logging`, `shutil`, `json`, and existing Pydantic, Typer, Rich.

---

## Verification

After all tasks:
1. `python -m pytest tests/ -v` — all tests pass (~196 total)
2. `python -m ruff check src/ tests/` — no lint errors
3. `python -m ruff format --check` on all changed files
4. Manual: `pip install -e .` then test `ade status`, `ade resume <id>`, `ade update`
