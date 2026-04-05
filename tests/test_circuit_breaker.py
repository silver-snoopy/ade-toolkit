from __future__ import annotations

import json
from pathlib import Path

from ade.circuit_breaker import (
    MAX_CODE_REVIEW_CYCLES,
    MAX_DESIGN_CHECK_ITERATIONS,
    MAX_QA_FIX_ITERATIONS,
    CircuitBreakerResult,
    check_circuit_breaker,
)
from ade.config import OrchestrationConfig
from ade.tasks import create_task, increment_iteration


def test_constants() -> None:
    assert MAX_DESIGN_CHECK_ITERATIONS == 2
    assert MAX_CODE_REVIEW_CYCLES == 3
    assert MAX_QA_FIX_ITERATIONS == 3


def test_all_clear(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.OK


def test_design_check_limit(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    for _ in range(MAX_DESIGN_CHECK_ITERATIONS):
        increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="design_check")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.DESIGN_CHECK_LIMIT


def test_code_review_limit(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    for _ in range(MAX_CODE_REVIEW_CYCLES):
        increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="code_review")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.CODE_REVIEW_LIMIT


def test_qa_fix_limit(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    for _ in range(MAX_QA_FIX_ITERATIONS):
        increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="qa_fix")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.QA_FIX_LIMIT


def test_under_limit_ok(tmp_path: Path) -> None:
    ade_dir = tmp_path / ".ade"
    ade_dir.mkdir()
    state = create_task(ade_dir=ade_dir, description="Test")
    increment_iteration(ade_dir=ade_dir, task_id=state.task_id, counter="qa_fix")
    result = check_circuit_breaker(ade_dir=ade_dir, task_id=state.task_id)
    assert result == CircuitBreakerResult.OK


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
