from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from ade.crew.ollama import check_ollama_health, ensure_model_available, list_models, pull_model


def _mock_response(data: dict, status: int = 200) -> MagicMock:
    """Create a mock HTTP response."""
    mock = MagicMock()
    mock.status = status
    mock.read.return_value = json.dumps(data).encode()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_check_health_returns_true_when_running() -> None:
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_response({"models": []})
        assert check_ollama_health() is True


def test_check_health_returns_false_when_down() -> None:
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = OSError("Connection refused")
        assert check_ollama_health() is False


def test_list_models_returns_model_names() -> None:
    models_data = {
        "models": [
            {"name": "gemma4:31b"},
            {"name": "qwen2.5-coder:14b"},
        ]
    }
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_response(models_data)
        result = list_models()
    assert result == ["gemma4:31b", "qwen2.5-coder:14b"]


def test_list_models_returns_empty_when_down() -> None:
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = OSError("Connection refused")
        assert list_models() == []


def test_ensure_model_available_found() -> None:
    with patch("ade.crew.ollama.list_models", return_value=["gemma4:31b"]):
        assert ensure_model_available("gemma4:31b") is True


def test_ensure_model_available_not_found() -> None:
    with patch("ade.crew.ollama.list_models", return_value=["gemma4:31b"]):
        assert ensure_model_available("llama3:8b") is False


def test_pull_model_success() -> None:
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value = _mock_response({}, status=200)
        result = pull_model("gemma4:31b")
    assert "pulled successfully" in result


def test_pull_model_failure() -> None:
    with patch("ade.crew.ollama.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = OSError("Connection refused")
        result = pull_model("gemma4:31b")
    assert "Failed" in result
