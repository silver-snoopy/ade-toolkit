"""Handoff report — structured logging for local LLM dispatch attempts."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class HandoffStatus(StrEnum):
    SUCCESS = "success"
    OLLAMA_DOWN = "ollama_down"
    MODEL_NOT_FOUND = "model_not_found"
    AGENT_CONFIG_ERROR = "agent_config_error"
    EXECUTION_ERROR = "execution_error"
    MAX_ITERATIONS = "max_iterations"
    TIMEOUT = "timeout"


class HandoffReport:
    """Records a structured handoff attempt for the orchestrator to read."""

    def __init__(
        self,
        *,
        task_id: str,
        phase: str,
        agent_name: str,
        model: str,
    ) -> None:
        self.task_id = task_id
        self.phase = phase
        self.agent_name = agent_name
        self.model = model
        self.status: HandoffStatus = HandoffStatus.SUCCESS
        self.error_message: str = ""
        self.error_category: str = ""
        self.recommendation: str = ""
        self.started_at: str = datetime.now(UTC).isoformat(timespec="seconds")
        self.finished_at: str = ""
        self.duration_seconds: float = 0.0

    def fail(
        self,
        status: HandoffStatus,
        error_message: str,
        recommendation: str = "",
    ) -> None:
        """Mark the handoff as failed with diagnosis."""
        self.status = status
        self.error_message = error_message
        self.error_category = _categorize_error(error_message)
        self.recommendation = recommendation or _default_recommendation(status)

    def complete(self) -> None:
        """Mark the handoff as successfully completed."""
        self.status = HandoffStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        self.finished_at = datetime.now(UTC).isoformat(timespec="seconds")
        return {
            "task_id": self.task_id,
            "phase": self.phase,
            "agent_name": self.agent_name,
            "model": self.model,
            "status": self.status.value,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "recommendation": self.recommendation,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def save(self, task_dir: Path) -> Path:
        """Write the handoff report to the task directory. Returns the file path."""
        report_dir = task_dir / "handoffs"
        report_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        filename = f"{self.phase}_{ts}.json"
        path = report_dir / filename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))
        return path


def _categorize_error(error_message: str) -> str:
    """Categorize an error message for the orchestrator."""
    msg = error_message.lower()
    if "cuda out of memory" in msg or "out of memory" in msg:
        return "gpu_oom"
    if "connection refused" in msg or "urlopen" in msg:
        return "ollama_connection"
    if "max iterations" in msg:
        return "agent_loop"
    if "timeout" in msg or "timed out" in msg:
        return "inference_timeout"
    if "not found" in msg:
        return "model_missing"
    return "unknown"


def _default_recommendation(status: HandoffStatus) -> str:
    """Provide a default recommendation based on failure status."""
    recommendations = {
        HandoffStatus.OLLAMA_DOWN: "Start Ollama with 'ollama serve' and retry",
        HandoffStatus.MODEL_NOT_FOUND: "Pull the model with 'ollama pull <model>' and retry",
        HandoffStatus.AGENT_CONFIG_ERROR: "Check .ade/crew/<agent>.yaml config and retry",
        HandoffStatus.EXECUTION_ERROR: "Check progress.log for details; may need fallback model",
        HandoffStatus.MAX_ITERATIONS: "Agent hit iteration limit; review partial output",
        HandoffStatus.TIMEOUT: "Inference timed out; try smaller context or fallback model",
    }
    return recommendations.get(status, "Escalate to human")
