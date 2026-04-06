"""Tests for handoff report — structured logging for local LLM dispatch."""

from __future__ import annotations

import json
from pathlib import Path

from ade.crew.handoff import (
    HandoffReport,
    HandoffStatus,
    _categorize_error,
    _default_recommendation,
)


def test_handoff_report_success(tmp_path: Path) -> None:
    report = HandoffReport(
        task_id="abc123",
        phase="code",
        agent_name="coder",
        model="gemma4:31b",
    )
    report.complete()
    data = report.to_dict()
    assert data["status"] == "success"
    assert data["task_id"] == "abc123"
    assert data["phase"] == "code"
    assert data["model"] == "gemma4:31b"
    assert data["error_message"] == ""


def test_handoff_report_failure(tmp_path: Path) -> None:
    report = HandoffReport(
        task_id="abc123",
        phase="code",
        agent_name="coder",
        model="gemma4:31b",
    )
    report.fail(
        HandoffStatus.OLLAMA_DOWN,
        "Ollama service is not responding",
    )
    data = report.to_dict()
    assert data["status"] == "ollama_down"
    assert data["error_message"] == "Ollama service is not responding"
    assert "ollama serve" in data["recommendation"].lower()


def test_handoff_report_save(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    report = HandoffReport(
        task_id="abc123",
        phase="code",
        agent_name="coder",
        model="gemma4:31b",
    )
    report.complete()
    path = report.save(task_dir)
    assert path.exists()
    assert path.parent.name == "handoffs"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "success"


def test_handoff_report_save_no_tmp_remnant(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks" / "abc123"
    task_dir.mkdir(parents=True)
    report = HandoffReport(
        task_id="abc123",
        phase="stubs",
        agent_name="architect",
        model="gemma4:31b",
    )
    report.complete()
    report.save(task_dir)
    tmp_files = list((task_dir / "handoffs").glob("*.tmp"))
    assert tmp_files == []


def test_categorize_error_gpu_oom() -> None:
    assert _categorize_error("CUDA out of memory") == "gpu_oom"


def test_categorize_error_connection() -> None:
    assert _categorize_error("Connection refused") == "ollama_connection"


def test_categorize_error_agent_loop() -> None:
    assert _categorize_error("Max iterations reached") == "agent_loop"


def test_categorize_error_timeout() -> None:
    assert _categorize_error("Request timed out") == "inference_timeout"


def test_categorize_error_model_missing() -> None:
    assert _categorize_error("Model 'foo' not found") == "model_missing"


def test_categorize_error_unknown() -> None:
    assert _categorize_error("Something weird happened") == "unknown"


def test_default_recommendations() -> None:
    assert "ollama serve" in _default_recommendation(HandoffStatus.OLLAMA_DOWN).lower()
    assert "pull" in _default_recommendation(HandoffStatus.MODEL_NOT_FOUND).lower()
    assert "config" in _default_recommendation(HandoffStatus.AGENT_CONFIG_ERROR).lower()
    assert "fallback" in _default_recommendation(HandoffStatus.EXECUTION_ERROR).lower()
    assert "partial" in _default_recommendation(HandoffStatus.MAX_ITERATIONS).lower()
    assert "fallback" in _default_recommendation(HandoffStatus.TIMEOUT).lower()


def test_handoff_status_values() -> None:
    assert HandoffStatus.SUCCESS == "success"
    assert HandoffStatus.OLLAMA_DOWN == "ollama_down"
    assert HandoffStatus.MODEL_NOT_FOUND == "model_not_found"
    assert HandoffStatus.AGENT_CONFIG_ERROR == "agent_config_error"
    assert HandoffStatus.EXECUTION_ERROR == "execution_error"
    assert HandoffStatus.MAX_ITERATIONS == "max_iterations"
    assert HandoffStatus.TIMEOUT == "timeout"


def test_handoff_report_model_not_found() -> None:
    report = HandoffReport(
        task_id="abc123",
        phase="test",
        agent_name="tester",
        model="qwen2.5-coder:14b",
    )
    report.fail(
        HandoffStatus.MODEL_NOT_FOUND,
        "Model 'qwen2.5-coder:14b' not found in Ollama",
    )
    data = report.to_dict()
    assert data["status"] == "model_not_found"
    assert data["error_category"] == "model_missing"
    assert "pull" in data["recommendation"].lower()
