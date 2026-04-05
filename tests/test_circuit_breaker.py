from __future__ import annotations

from pathlib import Path

from ade.circuit_breaker import (
    MAX_CODE_REVIEW_CYCLES,
    MAX_DESIGN_CHECK_ITERATIONS,
    MAX_QA_FIX_ITERATIONS,
    CircuitBreakerResult,
    check_circuit_breaker,
)
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
