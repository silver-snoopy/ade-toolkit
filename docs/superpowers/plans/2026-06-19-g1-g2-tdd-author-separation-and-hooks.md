# G1 + G2: Author-separated TDD & deterministic hook layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close ADE gaps G1 (author-separated TDD in Phase 4) and G2 (a deterministic, agent-selectable `git`-commit-time hook layer), wired for Claude Code and GitHub Copilot interchangeably.

**Architecture:** Two language-agnostic Python check scripts live in the committed `.claude/hooks/` directory (present in every git worktree). The same scripts are triggered two ways, chosen by `ade init --agent {claude,copilot}`: Claude Code `settings.json` PreToolUse hooks, or a git `pre-commit` config. Phase 4 of the SDLC splits into a `test-writer` subagent (writes failing tests, commits them alone) and the existing coder subagents as implementers (write code to green, forbidden from editing tests). The `block-mixed-commit` hook structurally enforces the separation.

**Tech Stack:** Python 3.11+, Typer CLI, Jinja2 templates (`PackageLoader("ade","templates")`), pytest, `typer.testing.CliRunner`, ruff. Generated hook scripts use only the Python stdlib.

**Spec:** `docs/superpowers/specs/2026-06-19-g1-g2-tdd-author-separation-and-hooks-design.md`

---

## File Structure

**New template files** (under `src/ade/templates/`):
- `hooks/_hooklib.py.j2` — shared classification/stub patterns + staged-file & message gathering for both substrates.
- `hooks/block-mixed-commit.py.j2` — rejects a commit mixing test + non-test source (G1 enforcer).
- `hooks/check-leftover-stub.py.j2` — rejects committed non-test source still containing stub markers.
- `claude_settings.json.j2` — Claude-mode wiring (PreToolUse → Bash → the two scripts).
- `pre-commit-config.yaml.j2` — Copilot-mode wiring (`repo: local` hooks).
- `agents/test-writer.md.j2` — new Sonnet test-author subagent.

**Edited template files:**
- `skills/phases/04-implement.md.j2` — rewrite to test-writer → implementer.
- `skills/ade-code.md.j2`, `skills/ade-full.md.j2` — Phase 4 wiring + author-separation note.
- `agents/backend-coder.md.j2`, `agents/frontend-coder.md.j2` — "never create or edit test files".
- `claude_md_section.md.j2` — Phase 4 one-line summary.

**Edited source:**
- `src/ade/cli.py` — `--agent` option; render `.claude/hooks/`; merge `settings.json` (claude) / seed `.pre-commit-config.yaml` (copilot); doctor checks.

**Edited docs:**
- `docs/ade-architecture-design.md` — Phase 4, subagent catalog, invariants, circuit breakers.

**New tests:**
- `tests/test_hooks.py` — render the hook templates into a temp git repo, exercise both scripts end-to-end under git-argv and Claude-stdin invocation.
- `tests/test_cli.py` — extend with `--agent` mode tests; fix the obsolete v3 negative assertion.

---

## Task 1: Hook scripts (`_hooklib`, `block-mixed-commit`, `check-leftover-stub`) + behavioral tests

**Files:**
- Create: `src/ade/templates/hooks/_hooklib.py.j2`
- Create: `src/ade/templates/hooks/block-mixed-commit.py.j2`
- Create: `src/ade/templates/hooks/check-leftover-stub.py.j2`
- Test: `tests/test_hooks.py`

> The scripts are static Python (no Jinja variables), so rendering them is an identity
> transform. The test renders the three templates into a temp `.claude/hooks/`, makes a
> real temp git repo, stages files, runs each script via subprocess, and asserts exit
> codes. Exit `0` = pass, exit `2` = reject (the contract both substrates share).

- [ ] **Step 1: Write the test harness + first failing test (`tests/test_hooks.py`)**

```python
import subprocess
import sys
from pathlib import Path

import pytest

from ade.cli import _get_template_env

HOOK_TEMPLATES = ("_hooklib.py", "block-mixed-commit.py", "check-leftover-stub.py")


def _render_hooks(dest: Path) -> None:
    """Render the hook templates into dest/.claude/hooks/."""
    env = _get_template_env()
    hooks_dir = dest / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for name in HOOK_TEMPLATES:
        content = env.get_template(f"hooks/{name}.j2").render()
        (hooks_dir / name).write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )


@pytest.fixture
def hook_repo(tmp_path: Path) -> Path:
    """A temp git repo with the ADE hooks rendered into .claude/hooks/."""
    _render_hooks(tmp_path)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", ".claude")
    _git(tmp_path, "commit", "-q", "-m", "chore: hooks")
    return tmp_path


def _run_hook(repo: Path, script: str, *argv: str) -> subprocess.CompletedProcess:
    """Run a hook in git/pre-commit mode (staged filenames passed as argv)."""
    return subprocess.run(
        [sys.executable, str(repo / ".claude" / "hooks" / script), *argv],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_stage(repo: Path, rel: str, content: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(repo, "add", rel)


def test_block_mixed_commit_rejects_test_plus_impl(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "src/feature.py", "tests/test_feature.py")
    assert result.returncode == 2, result.stderr
    assert "mixes test and implementation" in result.stderr
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_hooks.py::test_block_mixed_commit_rejects_test_plus_impl -v`
Expected: FAIL — `TemplateNotFound: hooks/_hooklib.py.j2`.

- [ ] **Step 3: Create `src/ade/templates/hooks/_hooklib.py.j2`**

```python
"""Shared helpers for ADE deterministic commit hooks.

Runs under two substrates with one exit-code contract (0 = pass, 2 = reject):
- git / pre-commit: staged filenames arrive as argv; the commit message (when a stage
  provides it) is read from $PRE_COMMIT_COMMIT_MSG_FILENAME.
- Claude Code PreToolUse(Bash): invoked with `--stdin-json`; the tool payload is read
  from stdin, the command is confirmed to be a `git commit`, and any -m message is
  parsed. Staged files come from `git diff --cached`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

BLOCK = 2  # Claude Code treats exit 2 as a hard block; non-zero fails a git commit.

_TEST_PATTERNS = (
    re.compile(r"(^|/)(tests?|specs?|e2e|__tests__)/", re.I),
    re.compile(r"(^|/)test_[^/]+$", re.I),
    re.compile(r"_test\.[a-z0-9]+$", re.I),
    re.compile(r"\.(test|spec)\.[a-z0-9]+$", re.I),
)

_SOURCE_EXTS = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".swift", ".rb", ".cs",
    ".cpp", ".cc", ".c", ".h", ".hpp", ".php", ".scala",
}

_STUB_PATTERNS = (
    re.compile(r"NotImplementedError"),
    re.compile(r"\bnot implemented\b", re.I),
    re.compile(r"(TODO|FIXME)\s*:?\s*implement", re.I),
    re.compile(r"""throw new Error\(\s*['"][^'"]*not implemented""", re.I),
    re.compile(r"\btodo!\s*\("),
    re.compile(r"\bunimplemented!\s*\("),
)


def is_test_file(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(rx.search(p) for rx in _TEST_PATTERNS)


def is_source_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in _SOURCE_EXTS


def has_stub(text: str) -> bool:
    return any(rx.search(text) for rx in _STUB_PATTERNS)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=False,
    ).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def staged_content(path: str) -> str:
    out = subprocess.run(
        ["git", "show", f":{path}"], capture_output=True, text=True, check=False
    )
    if out.returncode == 0:
        return out.stdout
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def gather() -> tuple[list[str], str]:
    """Return (changed_files, commit_message) for either substrate."""
    if "--stdin-json" in sys.argv:
        raw = sys.stdin.read().strip()
        payload = json.loads(raw) if raw else {}
        command = str(payload.get("tool_input", {}).get("command", ""))
        if "git commit" not in command:
            return [], ""
        m = re.search(r"-m\s+(['\"])(.*?)\1", command, re.S)
        return staged_files(), (m.group(2) if m else "")
    msg_file = os.environ.get("PRE_COMMIT_COMMIT_MSG_FILENAME")
    if msg_file and os.path.exists(msg_file):
        return staged_files(), _read(msg_file)
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    return (argv or staged_files()), ""
```

- [ ] **Step 4: Create `src/ade/templates/hooks/block-mixed-commit.py.j2`**

```python
#!/usr/bin/env python3
"""Reject a commit that mixes test files with non-test source files (ADE G1).

The test-writer commits tests alone; the implementer commits code alone. A single
commit must not contain both. Bypass with a `[test-refactor]` marker in the commit
message for the legitimate refactor-tests-with-code case.
"""
from __future__ import annotations

import sys

import _hooklib as h


def main() -> int:
    files, message = h.gather()
    if "[test-refactor]" in message:
        return 0
    source = [f for f in files if h.is_source_file(f)]
    tests = [f for f in source if h.is_test_file(f)]
    impl = [f for f in source if not h.is_test_file(f)]
    if tests and impl:
        sys.stderr.write(
            "ADE hook: commit mixes test and implementation files.\n"
            f"  tests: {', '.join(tests)}\n"
            f"  impl:  {', '.join(impl)}\n"
            "Commit tests and implementation separately "
            "(test-writer first, then implementer).\n"
            "Intentional test+code refactor? Add [test-refactor] to the message.\n"
        )
        return h.BLOCK
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Create `src/ade/templates/hooks/check-leftover-stub.py.j2`**

```python
#!/usr/bin/env python3
"""Reject committed non-test source still containing unfilled stub markers (ADE G2).

Phase 3 writes stubs (NotImplementedError / 'TODO: implement' / 'Not implemented') on
purpose; this hook ensures they are gone from non-test source by commit time.
"""
from __future__ import annotations

import sys

import _hooklib as h


def main() -> int:
    files, _ = h.gather()
    offenders = [
        f for f in files
        if h.is_source_file(f) and not h.is_test_file(f) and h.has_stub(h.staged_content(f))
    ]
    if offenders:
        sys.stderr.write(
            "ADE hook: unfilled stub markers in committed source:\n  "
            + "\n  ".join(offenders)
            + "\nImplement the stub before committing "
            "(NotImplementedError / 'TODO: implement' / 'Not implemented').\n"
        )
        return h.BLOCK
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the first test to verify it passes**

Run: `pytest tests/test_hooks.py::test_block_mixed_commit_rejects_test_plus_impl -v`
Expected: PASS.

- [ ] **Step 7: Add the remaining behavioral tests to `tests/test_hooks.py`**

```python
def test_block_mixed_commit_allows_test_only(hook_repo: Path) -> None:
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "tests/test_feature.py")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_allows_impl_only(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "src/feature.py")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_ignores_non_source(hook_repo: Path) -> None:
    # A markdown doc + impl is NOT a test+impl mix.
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "README.md", "# docs\n")
    result = _run_hook(hook_repo, "block-mixed-commit.py", "src/feature.py", "README.md")
    assert result.returncode == 0, result.stderr


def test_block_mixed_commit_marker_bypass(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    msg = hook_repo / "MSG"
    msg.write_text("refactor: rename [test-refactor]\n", encoding="utf-8")
    import os as _os
    env = dict(_os.environ, PRE_COMMIT_COMMIT_MSG_FILENAME=str(msg))
    result = subprocess.run(
        [sys.executable, str(hook_repo / ".claude" / "hooks" / "block-mixed-commit.py")],
        cwd=hook_repo, capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_rejects_stub_in_source(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/feature.py")
    assert result.returncode == 2, result.stderr
    assert "stub markers" in result.stderr


def test_check_leftover_stub_ignores_stub_in_test(hook_repo: Path) -> None:
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    raise NotImplementedError\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "tests/test_feature.py")
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_allows_clean_impl(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 42\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/feature.py")
    assert result.returncode == 0, result.stderr


def test_check_leftover_stub_rejects_js_throw(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/api.ts", "export function f() { throw new Error('Not implemented'); }\n")
    result = _run_hook(hook_repo, "check-leftover-stub.py", "src/api.ts")
    assert result.returncode == 2, result.stderr


def test_hooks_stdin_json_mode(hook_repo: Path) -> None:
    """Claude substrate: payload on stdin, --stdin-json flag, files via git diff --cached."""
    _write_stage(hook_repo, "src/feature.py", "def f():\n    return 1\n")
    _write_stage(hook_repo, "tests/test_feature.py", "def test_f():\n    assert True\n")
    payload = '{"tool_input": {"command": "git commit -m \\"feat: x\\""}}'
    result = subprocess.run(
        [sys.executable, str(hook_repo / ".claude" / "hooks" / "block-mixed-commit.py"), "--stdin-json"],
        cwd=hook_repo, input=payload, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2, result.stderr


def test_hooks_stdin_json_ignores_non_commit(hook_repo: Path) -> None:
    _write_stage(hook_repo, "src/feature.py", "def f():\n    raise NotImplementedError\n")
    payload = '{"tool_input": {"command": "ls -la"}}'
    result = subprocess.run(
        [sys.executable, str(hook_repo / ".claude" / "hooks" / "check-leftover-stub.py"), "--stdin-json"],
        cwd=hook_repo, input=payload, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
```

- [ ] **Step 8: Run the full hook test module**

Run: `pytest tests/test_hooks.py -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/ade/templates/hooks/ tests/test_hooks.py
git commit -m "feat: add deterministic commit hooks (block-mixed-commit, check-leftover-stub)"
```

---

## Task 2: `--agent` option, hook rendering, and mode wiring in `cli.py`

**Files:**
- Create: `src/ade/templates/claude_settings.json.j2`
- Create: `src/ade/templates/pre-commit-config.yaml.j2`
- Modify: `src/ade/cli.py` (init signature + helpers)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Create `src/ade/templates/claude_settings.json.j2`**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python .claude/hooks/block-mixed-commit.py --stdin-json" },
          { "type": "command", "command": "python .claude/hooks/check-leftover-stub.py --stdin-json" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Create `src/ade/templates/pre-commit-config.yaml.j2`**

```yaml
# ADE deterministic commit hooks (G1/G2).
# Install with BOTH hook types:
#   pre-commit install --hook-type pre-commit --hook-type commit-msg
repos:
  - repo: local
    hooks:
      - id: ade-block-mixed-commit
        name: ADE — no mixed test+impl commits
        entry: python .claude/hooks/block-mixed-commit.py
        language: system
        stages: [commit-msg]
      - id: ade-check-leftover-stub
        name: ADE — no leftover stubs in committed source
        entry: python .claude/hooks/check-leftover-stub.py
        language: system
        types: [text]
        stages: [pre-commit]
```

> Rationale: `block-mixed-commit` runs at the `commit-msg` stage so the `[test-refactor]`
> message bypass works (pre-commit sets `PRE_COMMIT_COMMIT_MSG_FILENAME` there);
> `check-leftover-stub` runs at `pre-commit` (no message needed). Both read staged files.

- [ ] **Step 3: Write failing CLI tests for the two modes (`tests/test_cli.py`)**

```python
def test_init_claude_mode_emits_settings_and_hooks(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    settings = python_project / ".claude" / "settings.json"
    assert settings.exists()
    assert "block-mixed-commit.py" in settings.read_text()
    # hook scripts are always emitted, in the committed .claude/hooks/ dir
    assert (python_project / ".claude" / "hooks" / "_hooklib.py").exists()
    assert (python_project / ".claude" / "hooks" / "block-mixed-commit.py").exists()
    assert (python_project / ".claude" / "hooks" / "check-leftover-stub.py").exists()
    # claude mode does NOT seed a pre-commit config
    assert not (python_project / ".pre-commit-config.yaml").exists()


def test_init_copilot_mode_emits_precommit_config(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--agent", "copilot"]
    )
    assert result.exit_code == 0
    cfg = python_project / ".pre-commit-config.yaml"
    assert cfg.exists()
    assert "ade-block-mixed-commit" in cfg.read_text()
    assert (python_project / ".claude" / "hooks" / "block-mixed-commit.py").exists()
    # copilot mode does NOT write claude settings hooks
    assert not (python_project / ".claude" / "settings.json").exists()


def test_init_rejects_unknown_agent(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--agent", "cursor"]
    )
    assert result.exit_code != 0


def test_init_settings_merge_is_idempotent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    import json
    settings = json.loads((python_project / ".claude" / "settings.json").read_text())
    cmds = [
        h["command"]
        for block in settings["hooks"]["PreToolUse"]
        for h in block["hooks"]
    ]
    assert cmds.count("python .claude/hooks/block-mixed-commit.py --stdin-json") == 1


def test_init_settings_merge_preserves_existing(python_project: Path) -> None:
    import json
    settings_path = python_project / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}))
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    merged = json.loads(settings_path.read_text())
    assert merged["permissions"]["allow"] == ["Bash(ls)"]
    assert "PreToolUse" in merged["hooks"]


def test_init_copilot_seed_if_missing_preserves_existing(python_project: Path) -> None:
    cfg = python_project / ".pre-commit-config.yaml"
    cfg.write_text("repos: []  # user owned\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project), "--agent", "copilot"])
    assert "user owned" in cfg.read_text()
```

- [ ] **Step 4: Run them to verify they fail**

Run: `pytest tests/test_cli.py -k "claude_mode or copilot_mode or unknown_agent or merge or seed_if_missing" -v`
Expected: FAIL (option `--agent` not defined; settings/hooks not emitted).

- [ ] **Step 5: Add the merge/seed helpers to `src/ade/cli.py`**

Add `import json` to the top imports (alongside the existing imports), then add these helpers above `init`:

```python
def _render_hooks(env: Environment, hooks_dir: Path, context: dict) -> None:
    """Render the deterministic hook scripts, preserving exact filenames.

    Rendered explicitly (not via _render_template_dir) so the leading-underscore
    helper `_hooklib.py` is not mangled into a dashed name.
    """
    for name in ("_hooklib.py", "block-mixed-commit.py", "check-leftover-stub.py"):
        _render_and_write(env, f"hooks/{name}.j2", hooks_dir / name, context)


def _merge_hooks(current: dict, ade: dict) -> dict:
    """Idempotently merge ADE PreToolUse hook commands into an existing settings dict."""
    merged = dict(current)
    hooks = merged.setdefault("hooks", {})
    for event, blocks in ade.get("hooks", {}).items():
        existing_blocks = hooks.setdefault(event, [])
        for ade_block in blocks:
            target = next(
                (b for b in existing_blocks if b.get("matcher") == ade_block.get("matcher")),
                None,
            )
            if target is None:
                existing_blocks.append(ade_block)
                continue
            target_hooks = target.setdefault("hooks", [])
            seen = {h.get("command") for h in target_hooks}
            for hook in ade_block.get("hooks", []):
                if hook.get("command") not in seen:
                    target_hooks.append(hook)
    return merged


def _emit_claude_hooks(env: Environment, project_dir: Path, context: dict) -> str:
    """Create or idempotently merge .claude/settings.json hooks. Returns action word."""
    dest = project_dir / ".claude" / "settings.json"
    ade_settings = json.loads(env.get_template("claude_settings.json.j2").render(**context))
    if dest.exists():
        try:
            current = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
        merged = _merge_hooks(current, ade_settings)
        action = "Merged hooks into"
    else:
        merged = ade_settings
        action = "Created"
    _write_file(dest, json.dumps(merged, indent=2) + "\n")
    return action
```

- [ ] **Step 6: Add the `--agent` option and wiring to `init`**

In the `init` signature, add after the `language` option:

```python
    agent: Annotated[
        str,
        typer.Option(help="Target agent for hook wiring: 'claude' or 'copilot'"),
    ] = "claude",
```

After the language-override block (right after `rprint(f"  Project name: {info.project_name}")`), validate the mode:

```python
    if agent not in {"claude", "copilot"}:
        rprint(f"[red]Error: --agent must be 'claude' or 'copilot', got '{agent}'[/red]")
        raise typer.Exit(1)
```

After the commands directory is rendered (right after the `_render_template_dir(env, "commands/", commands_dir, ctx)` line), add:

```python
    # Deterministic commit hooks (G1/G2) — scripts always emitted to the committed
    # .claude/hooks/ dir so they exist inside git worktrees; wiring is mode-specific.
    _render_hooks(env, project_dir / ".claude" / "hooks", ctx)

    if agent == "claude":
        action = _emit_claude_hooks(env, project_dir, ctx)
        rprint(f"  [green]+[/green] {action} .claude/settings.json (hook wiring)")
    else:  # copilot
        created = _render_and_write_if_missing(
            env, "pre-commit-config.yaml.j2", project_dir / ".pre-commit-config.yaml", ctx
        )
        if created:
            rprint("  [green]+[/green] Created .pre-commit-config.yaml")
            rprint(
                "    [dim]run: pre-commit install --hook-type pre-commit --hook-type commit-msg[/dim]"
            )
        else:
            rprint("  [dim]= Kept existing .pre-commit-config.yaml[/dim]")
            rprint("    [dim]Add the ADE `repo: local` hooks block manually — see docs.[/dim]")
```

- [ ] **Step 7: Fix the obsolete v3 negative assertion in `tests/test_cli.py`**

Replace the body of `test_init_does_not_generate_v3_artifacts` so it no longer asserts
the absence of `settings.json` (claude mode now creates it). Keep the genuine v3 checks:

```python
def test_init_does_not_generate_v3_artifacts(python_project: Path) -> None:
    """v4 should NOT generate CrewAI or Ollama artifacts."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    assert not (python_project / ".ade" / "config.yaml").exists()
    assert not (python_project / ".ade" / "crew").exists()
    assert not (python_project / ".ade" / "modelfiles").exists()
    # Default (claude) mode does not seed a pre-commit config; copilot mode does.
    assert not (python_project / ".pre-commit-config.yaml").exists()
```

- [ ] **Step 8: Run the CLI tests**

Run: `pytest tests/test_cli.py -v`
Expected: all PASS (including the new mode tests and the fixed v3 test).

- [ ] **Step 9: Commit**

```bash
git add src/ade/cli.py src/ade/templates/claude_settings.json.j2 src/ade/templates/pre-commit-config.yaml.j2 tests/test_cli.py
git commit -m "feat: add ade init --agent {claude,copilot} hook wiring"
```

---

## Task 3: Doctor mode-awareness

**Files:**
- Modify: `src/ade/cli.py` (`doctor` command)
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write a failing test**

```python
def test_doctor_checks_hook_scripts(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    with patch("ade.cli._check_command", return_value=True):
        ok = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert ok.exit_code == 0
    assert "hook" in ok.output.lower()

    # Removing a hook script should make doctor FAIL.
    (python_project / ".claude" / "hooks" / "block-mixed-commit.py").unlink()
    with patch("ade.cli._check_command", return_value=True):
        bad = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert bad.exit_code == 1
    assert "FAIL" in bad.output
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_doctor_checks_hook_scripts -v`
Expected: FAIL (doctor does not yet check hooks).

- [ ] **Step 3: Add hook checks to `doctor`**

In `doctor`, append to the `required_paths` list (after the existing research-phase entry):

```python
        (".claude/hooks/block-mixed-commit.py", "Commit hook: block-mixed-commit (G1)"),
        (".claude/hooks/check-leftover-stub.py", "Commit hook: check-leftover-stub (G2)"),
```

Then, immediately after the bootstrap-artifacts loop (before the "Peer plugins" section), add a mode-aware nudge:

```python
    # Hook wiring nudge (mode is inferred from which wiring file exists).
    if (project_dir / ".pre-commit-config.yaml").exists():
        if _check_command("pre-commit"):
            rprint(
                "  [dim]copilot hook wiring detected — ensure hooks are installed:\n"
                "    pre-commit install --hook-type pre-commit --hook-type commit-msg[/dim]"
            )
        else:
            rprint("  [yellow]WARN[/yellow]  .pre-commit-config.yaml present but 'pre-commit' not installed")
            warnings += 1
```

- [ ] **Step 4: Run the doctor tests**

Run: `pytest tests/test_cli.py -k doctor -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ade/cli.py tests/test_cli.py
git commit -m "feat: doctor checks commit hooks and pre-commit install state"
```

---

## Task 4: Phase 4 split — `test-writer` agent, coder rules, skill rewrite

**Files:**
- Create: `src/ade/templates/agents/test-writer.md.j2`
- Modify: `src/ade/templates/agents/backend-coder.md.j2`, `src/ade/templates/agents/frontend-coder.md.j2`
- Modify: `src/ade/templates/skills/phases/04-implement.md.j2`
- Modify: `src/ade/templates/skills/ade-code.md.j2`, `src/ade/templates/skills/ade-full.md.j2`
- Modify: `src/ade/templates/claude_md_section.md.j2`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_init_generates_test_writer_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent = python_project / ".claude" / "agents" / "test-writer.md"
    assert agent.exists()
    content = agent.read_text()
    assert "model:" in content and "sonnet" in content
    assert "failing" in content.lower()
    assert "never" in content.lower() and "implementation" in content.lower()


def test_coders_forbidden_from_test_files(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    backend = (python_project / ".claude" / "agents" / "backend-coder.md").read_text()
    assert "test file" in backend.lower()


def test_phase4_skill_describes_author_separation(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    phase4 = (python_project / ".claude" / "skills" / "ade" / "phases" / "04-implement.md").read_text()
    assert "test-writer" in phase4
    assert "RED" in phase4 or "failing test" in phase4.lower()
    assert "author separation" in phase4.lower() or "separate" in phase4.lower()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_cli.py -k "test_writer or coders_forbidden or author_separation" -v`
Expected: FAIL.

- [ ] **Step 3: Create `src/ade/templates/agents/test-writer.md.j2`**

```markdown
---
model: sonnet
tools: [Read, Write, Edit, Bash, Glob, Grep]
---
You are a test author working in a git worktree. You write FAILING tests that pin down
the behavior the implementer must satisfy. You NEVER write implementation code.

Rules:
- Write tests ONLY. Create or edit test files only (e.g. `*_test.*`, `test_*.*`,
  `*.test.*`, `*.spec.*`, or files under `tests/`, `spec/`, `e2e/`). Never touch
  non-test source.
- Base every test on the spec's acceptance criteria and the Phase-3 stub signatures.
  Import the real signatures; do not redefine them.
- The suite MUST be RED for the right reason: tests fail because the logic is
  unimplemented, NOT because of import errors or collection failures. Run the suite and
  confirm the failures are assertion/behavior failures before finishing.
- Commit your tests as a single test-only commit: `test: add failing tests for <task-id>`.
  A commit hook rejects commits that mix tests with implementation — keep them separate.
- Do not weaken or delete tests to make them pass; that is the implementer's job to
  satisfy, not yours to avoid.
```

- [ ] **Step 4: Add the no-test-files rule to both coder agents**

In `src/ade/templates/agents/backend-coder.md.j2`, change the rules list to include the
test-file prohibition. Replace the existing rules block with:

```markdown
You are a backend developer implementing features in a git worktree. You make the
test-writer's FAILING tests pass by writing the minimum correct implementation.

Rules:
- Follow the project's conventions in CLAUDE.md
- Only edit files assigned to you — never touch files outside your assignment
- NEVER create or edit test files. Tests are owned by the test-writer; a commit hook
  rejects commits that mix tests with implementation. If a test looks wrong, report it
  to the orchestrator rather than editing it.
- Replace every stub: no `Not implemented` / `NotImplementedError` / `TODO: implement`
  may remain in source you commit (a commit hook enforces this).
- Use Edit for existing files, Write only for new files
- Run the build and the test suite after changes to verify it goes green
- Commit implementation as its own commit: `feat: …` / `fix: …`
```

In `src/ade/templates/agents/frontend-coder.md.j2`, replace its rules block with:

```markdown
You are a frontend developer implementing UI features in a git worktree. You make the
test-writer's FAILING tests pass by writing the minimum correct implementation.

Rules:
- Follow the project's conventions in CLAUDE.md
- Only edit files assigned to you — never touch files outside your assignment
- NEVER create or edit test files. Tests are owned by the test-writer; a commit hook
  rejects commits that mix tests with implementation.
- Replace every stub: no `Not implemented` / `NotImplementedError` / `TODO: implement`
  may remain in source you commit (a commit hook enforces this).
- Use Edit for existing files, Write only for new files
- Ensure components are accessible and responsive
- Run the build and the test suite after changes to verify it goes green
- Commit implementation as its own commit: `feat: …` / `fix: …`
```

- [ ] **Step 5: Rewrite `src/ade/templates/skills/phases/04-implement.md.j2`**

Replace the file's "## Purpose" section and add a new author-separation section at the
top of the body (keep the existing Build Order, File Ownership, Convention Reference,
and Scope-drift sections intact below it). Insert this immediately after the `# Phase 4
— Implement` heading:

```markdown
## Purpose

Turn the spec into working code using **author-separated TDD**. Phase 4 runs in two
ordered sub-steps inside the worktree created during Design Check
(`.ade/worktrees/<task-id>`). The Phase-3 stubs define the shape; the tests define the
behavior; the implementer makes the tests pass.

## 4a — Test-writer (RED)

Dispatch the `test-writer` subagent. It:
- Reads the spec's acceptance criteria and the Phase-3 stub signatures.
- Writes FAILING tests (test files only).
- Confirms the suite is RED for the right reason (assertion failures, not import errors).
- Commits a **test-only** commit: `test: add failing tests for <task-id>`.

## 4b — Implementer (GREEN)

Dispatch the implementer subagent(s) (`backend-coder` / `frontend-coder`). They:
- Receive the spec, the committed failing tests, and the stubs.
- Write the minimum code to turn the suite GREEN.
- Must NOT create or edit test files, and must leave no stub markers in committed source.
- Commit an **implementation-only** commit: `feat:` / `fix:`.

## Author-separation invariant

The orchestrator dispatches 4b **without** passing the test-writer's reasoning — the
implementer sees only the spec, the failing tests on disk, and the stubs. The
`block-mixed-commit` hook rejects any commit that mixes tests with implementation
(bypass only with a `[test-refactor]` marker, used in the optional refactor step). This
makes the generator≠verifier separation structural, not advisory.
```

- [ ] **Step 6: Update the composite skills `ade-code.md.j2` and `ade-full.md.j2`**

In `src/ade/templates/skills/ade-code.md.j2`, replace the `## Phase 4 — IMPLEMENT`
block with:

```markdown
## Phase 4 — IMPLEMENT (author-separated TDD)
Step 4a: dispatch `test-writer` → writes FAILING tests, commits them alone (`test:`).
Step 4b: dispatch implementer subagents (`backend-coder`/`frontend-coder`) → make tests
GREEN, commit alone (`feat:`/`fix:`). Enforce build order: shared → backend → frontend.
The orchestrator does NOT pass the test-writer's reasoning to the implementer.

**Hard requirement:** Tests start RED, end GREEN. No stub markers remain in source.
**Mechanism:** `block-mixed-commit` hook keeps test and impl commits separate.
**Exit criteria:** All tests pass. Build passes.
```

In `src/ade/templates/skills/ade-full.md.j2`, find the Phase 4 description and apply the
same two-step (test-writer → implementer) wording, preserving the surrounding
Exit-criteria / Hard-requirement / Allowed-fallback structure that the existing tests
assert on (`test_init_full_skill_has_exit_criteria`).

- [ ] **Step 7: Update `src/ade/templates/claude_md_section.md.j2`**

Find the Phase 4 line in the phase table/summary and change it to reflect the split,
e.g. `Phase 4 — Implement: test-writer (RED) → implementer (GREEN), author-separated`.

- [ ] **Step 8: Run the agent/skill tests + the full suite**

Run: `pytest tests/ -v`
Expected: all PASS (including the pre-existing `test_init_full_skill_*` assertions).

- [ ] **Step 9: Commit**

```bash
git add src/ade/templates/agents/test-writer.md.j2 src/ade/templates/agents/backend-coder.md.j2 src/ade/templates/agents/frontend-coder.md.j2 src/ade/templates/skills/phases/04-implement.md.j2 src/ade/templates/skills/ade-code.md.j2 src/ade/templates/skills/ade-full.md.j2 src/ade/templates/claude_md_section.md.j2 tests/test_cli.py
git commit -m "feat: split Phase 4 into test-writer and implementer (author-separated TDD)"
```

---

## Task 5: Architecture documentation

**Files:**
- Modify: `docs/ade-architecture-design.md`

- [ ] **Step 1: Update the 10-phase table (Phase 4 row)**

Change the Phase 4 row's "Primary actor" / "Output" to reflect the split:
`4 — Implement | Author-separated TDD | test-writer (RED) → 1–3 implementer subagents (GREEN) | Tests + code in worktree`.

- [ ] **Step 2: Add `test-writer` to the Subagent catalog table**

Add a row: `| test-writer | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4a |`
and update the `backend-coder`/`frontend-coder` rows' "Used in" to "Phase 4b".

- [ ] **Step 3: Add the author-separation orchestrator invariant**

In "Orchestrator invariants", add:
`10. The Phase-4 implementer never receives the test-writer's reasoning, and never edits test files. The block-mixed-commit hook enforces that tests and implementation land in separate commits.`

- [ ] **Step 4: Document the hook layer + circuit breakers**

Add a short "Deterministic hook layer (G2)" subsection describing `.claude/hooks/`,
the two scripts, the `--agent {claude,copilot}` wiring, and the `[test-refactor]`
bypass. Note the hooks are a hard gate (reject, do not retry).

- [ ] **Step 5: Commit**

```bash
git add docs/ade-architecture-design.md
git commit -m "docs: document Phase 4 split and the deterministic hook layer"
```

---

## Task 6: Full verification & finalize

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -q`
Expected: all PASS, no errors.

- [ ] **Step 2: Lint & format**

Run: `ruff check src/ tests/` then `ruff format --check src/ tests/`
Expected: no errors. Fix any reported issues and re-run.

- [ ] **Step 3: Manual smoke test of both modes**

```bash
cd "$(mktemp -d)" && git init -q && printf '[project]\nname="smoke"\n' > pyproject.toml
ade init --agent claude   && test -f .claude/settings.json && test -f .claude/hooks/_hooklib.py && echo CLAUDE_OK
ade init --agent copilot  && test -f .pre-commit-config.yaml && echo COPILOT_OK
```
Expected: prints `CLAUDE_OK` and `COPILOT_OK` (second init merges settings idempotently; both leave hook scripts in place).

- [ ] **Step 4: Update the spec status line**

In `docs/superpowers/specs/2026-06-19-g1-g2-tdd-author-separation-and-hooks-design.md`,
change the status to `Implemented`.

- [ ] **Step 5: Final commit**

```bash
git add docs/superpowers/specs/2026-06-19-g1-g2-tdd-author-separation-and-hooks-design.md
git commit -m "chore: mark G1+G2 spec implemented"
```

---

## Self-review checklist (completed by plan author)

- **Spec coverage:** §3.1 Phase-4 split → Task 4; §3.2 check scripts → Task 1; §3.3
  install-mode → Task 2; §3.4 dual invocation → Task 1 (`gather()` + stdin tests);
  §3.5 idempotent emission → Task 2 (merge idempotent + seed-if-missing tests); §3.6
  CLI/doctor/docs → Tasks 2, 3, 5; §5 edge cases → Task 1 (marker bypass, non-source,
  stub-in-test) ✔
- **Placeholder scan:** all code steps contain complete code; commands have expected
  output ✔
- **Type/name consistency:** `_hooklib` helper names (`is_test_file`, `is_source_file`,
  `has_stub`, `staged_files`, `staged_content`, `gather`, `BLOCK`) used consistently
  across both scripts and tests; `_render_hooks`/`_merge_hooks`/`_emit_claude_hooks`
  referenced consistently in `init`; hook command strings identical in
  `claude_settings.json.j2`, the merge-idempotency test, and the rendered output ✔
