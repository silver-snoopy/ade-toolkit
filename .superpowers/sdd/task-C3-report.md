# Task C3 Report: Codex Adapter (TOML workers, native hooks, degraded-tier note)

## C0 Corrections Applied

1. **skills_dirs = `(".agents/skills",)` ONLY** — Codex reads `.agents/skills/` exclusively. Brief had `(".codex/skills", ".agents/skills")` — wrong, dropped `.codex/skills/`.

2. **`developer_instructions` key, not `instructions`; name + description synthesized** — Codex TOML requires `name`, `description`, `developer_instructions`. Brief had `instructions =` (wrong key). `_to_toml(markdown, name)` now synthesizes:
   - `name` = stem argument (e.g. `"implementer"`)
   - `description` = first non-empty line of body
   - `model` = frontmatter `model:` if present (optional)
   - `developer_instructions` = full body as TOML literal string (`'''...'''`)
   - `tools` frontmatter dropped (Codex TOML has no `tools` key)

3. **Hook wiring file: `.codex/hooks.json` (JSON)** — Brief said `codex_hooks.toml.j2` → `.codex/hooks.toml`; C0 verified Codex reads `.codex/hooks.json`. Created `codex_hooks.json.j2` with the JSON schema (PreToolUse → matcher=Bash → commands with timeout).

4. **`_wire_codex` emits `.codex/hooks.json` (not `.codex/hooks.toml`)** — Also emits `.ade/codex-degraded.md` note; `_hooklib` `_ENVELOPE["codex"]` unchanged (already `tool_input.command`, correct per C0).

## `_to_toml` Synthesis Approach

Parses the `--- frontmatter --- body` markdown. Extracts `model:` from frontmatter; drops `tools:`. Synthesizes `name` from the caller-supplied stem, `description` from the first non-empty body line, and emits the full body as `developer_instructions = '''...'''` (with `'''` → `''` escaping inside). Result is valid TOML.

## TDD Evidence

- `test_render_worker_toml_for_codex` in `tests/test_harnesses.py`: ran RED (KeyError: 'codex') before CODEX target added, then GREEN after.
- `test_codex_layout` in `tests/test_golden.py`: runs GREEN end-to-end via `ade init --agent codex`, asserting `.agents/skills/ade-research/SKILL.md`, `.codex/agents/implementer.toml` (with `developer_instructions =` and `'''`), `AGENTS.md`, `.ade/codex-degraded.md`, `.codex/hooks.json` (PreToolUse, --harness codex), and absence of a spurious copilot-instructions pointer.

## Golden Test

`test_codex_layout` asserts the full codex layout including hook JSON content, TOML structure, skills dir, memory file, degraded note. Pass.

## Full-Suite Result

103 passed (101 existing + 2 new). `ruff check` and `ruff format --check` clean.

## Self-Review

- `_to_toml` correctly synthesizes all required Codex keys and drops unsupported ones.
- `_wire_codex` is symmetric with `_wire_copilot` (overwrite; always-owned ADE file).
- `_ENVELOPE["codex"]` in `_hooklib.py.j2` untouched — already correct per C0.
- `TARGETS["codex"]` registered; `selected_targets("codex")` and `selected_targets("all")` both resolve correctly.

## Concerns

- `description` synthesis (first body line) produces the full first sentence. If a worker's body starts with a heading or blank line the fallback is an empty string — acceptable for V1 since current templates all start with a role sentence.
- Codex `emit_memory_pointer` still writes an AGENTS.md block (memory.py calls `_render_and_write_if_missing`). Since AGENTS.md is the canonical memory file and Codex reads it natively, this is correct — no separate pointer file is needed and none is emitted.

## Fix: TOML string escaping (post-C3 review)

**Status:** PASS

**Issue:** `_to_toml` builds TOML double-quoted values without escaping backslash or quote characters. If a markdown worker's `description` (or `model` frontmatter) contains `"` or `\`, the generated TOML is invalid.

**Fix Applied:**
1. Added `_toml_basic_str(value: str)` helper to escape TOML basic-string values (backslash first, then quote).
2. Updated `_to_toml` to use `_toml_basic_str()` for `name`, `description`, and `model` fields.
3. Fixed docstring typo: changed `''` to `'''` in the `developer_instructions` description.
4. Added test `test_to_toml_escapes_quotes_in_description`: feeds markdown with a quote in the description, asserts the TOML parses via `tomllib.loads()`.

**Test Evidence:**
- RED: Test failed with `tomllib.TOMLDecodeError` (unescaped quote broke TOML syntax).
- GREEN: After adding `_toml_basic_str`, test passes; TOML parses cleanly.
- Full suite: **104 passed** (103 prior + 1 new).
- Lint & format: All checks passed.

**Commit:** `32e8fad` "fix(harnesses): escape TOML basic-string values in _to_toml"
