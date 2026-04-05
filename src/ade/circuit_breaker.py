"""Circuit breaker — prevents infinite agent loops by enforcing iteration limits."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from ade.tasks import load_task

MAX_DESIGN_CHECK_ITERATIONS = 2
MAX_CODE_REVIEW_CYCLES = 3
MAX_QA_FIX_ITERATIONS = 3


class CircuitBreakerResult(StrEnum):
    OK = "ok"
    DESIGN_CHECK_LIMIT = "design_check_limit"
    CODE_REVIEW_LIMIT = "code_review_limit"
    QA_FIX_LIMIT = "qa_fix_limit"


def check_circuit_breaker(ade_dir: Path, task_id: str) -> CircuitBreakerResult:
    """Check if any iteration limit has been reached."""
    state = load_task(ade_dir, task_id)

    if state.iterations.design_check >= MAX_DESIGN_CHECK_ITERATIONS:
        return CircuitBreakerResult.DESIGN_CHECK_LIMIT
    if state.iterations.code_review >= MAX_CODE_REVIEW_CYCLES:
        return CircuitBreakerResult.CODE_REVIEW_LIMIT
    if state.iterations.qa_fix >= MAX_QA_FIX_ITERATIONS:
        return CircuitBreakerResult.QA_FIX_LIMIT

    return CircuitBreakerResult.OK
