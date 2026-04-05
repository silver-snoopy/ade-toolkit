"""Ollama health check and model management utilities."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

OLLAMA_API_BASE = "http://localhost:11434"


def check_ollama_health() -> bool:
    """Check if Ollama is running by hitting the tags endpoint."""
    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def list_models() -> list[str]:
    """List available models from Ollama."""
    try:
        req = urllib.request.Request(f"{OLLAMA_API_BASE}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        return []


def ensure_model_available(model_name: str) -> bool:
    """Check if a model is available, return True if it is."""
    models = list_models()
    # Match exact name or base name (without tag) for flexibility
    return any(m == model_name or m.split(":")[0] == model_name.split(":")[0] for m in models)


def hot_swap_model(from_model: str, to_model: str) -> str:
    """Unload one model and load another to manage VRAM on single-GPU setups."""
    try:
        # Unload the current model
        payload = json.dumps({"model": from_model, "keep_alive": 0}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_API_BASE}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30):
            pass

        # Load the new model
        payload = json.dumps({"model": to_model, "keep_alive": "5m"}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_API_BASE}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60):
            pass

        return f"Swapped from '{from_model}' to '{to_model}'"
    except (urllib.error.URLError, OSError) as e:
        return f"Failed to swap models: {e}"


def pull_model(model_name: str) -> str:
    """Pull a model using Ollama API. Returns status message."""
    try:
        payload = json.dumps({"name": model_name}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_API_BASE}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            return f"Model '{model_name}' pulled successfully (status: {resp.status})"
    except urllib.error.URLError as e:
        return f"Failed to pull model '{model_name}': {e}"
    except OSError as e:
        return f"Failed to pull model '{model_name}': {e}"
