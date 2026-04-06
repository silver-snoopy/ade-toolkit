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
MAX_VERIFY_REJECT_ITERATIONS = 2
MAX_TOTAL_ITERATIONS = 11


class CircuitBreakerResult(StrEnum):
    OK = "ok"
    DESIGN_CHECK_LIMIT = "design_check_limit"
    CODE_REVIEW_LIMIT = "code_review_limit"
    QA_FIX_LIMIT = "qa_fix_limit"
    VERIFY_REJECT_LIMIT = "verify_reject_limit"
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
    verify_limit = getattr(config, "max_verify_iterations", None) if config else None
    if verify_limit is None:
        verify_limit = MAX_VERIFY_REJECT_ITERATIONS
    total_limit = config.max_total_iterations if config else MAX_TOTAL_ITERATIONS

    iters = state.iterations
    if iters.design_check >= design_limit:
        return CircuitBreakerResult.DESIGN_CHECK_LIMIT
    if iters.code_review >= review_limit:
        return CircuitBreakerResult.CODE_REVIEW_LIMIT
    if iters.qa_fix >= qa_limit:
        return CircuitBreakerResult.QA_FIX_LIMIT
    if iters.verify_reject >= verify_limit:
        return CircuitBreakerResult.VERIFY_REJECT_LIMIT
    if iters.design_check + iters.code_review + iters.qa_fix + iters.verify_reject >= total_limit:
        return CircuitBreakerResult.TOTAL_ITERATION_LIMIT

    return CircuitBreakerResult.OK
