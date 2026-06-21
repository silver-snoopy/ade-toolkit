# Harness Locations Reference

> **Purpose:** Verified constants for ADE v3.0.0 multi-harness support (Tasks C1–C3).
> Refresh this file when a vendor changes paths; `tests/test_locations.py` pins these constants.
> Values marked `UNVERIFIED` have a stated reason and a best-guess fallback for C1–C3.

---

## Claude (baseline)

### Skills dir(s)
- Project-level: `.claude/skills/<skill-name>/SKILL.md`
- User-level: `~/.claude/skills/<skill-name>/SKILL.md`

Source: Claude Code docs (built-in to this project; ground truth).

### Worker/subagent definition
- Directory: `.claude/agents/`
- Extension: `.md`
- Frontmatter keys: `name`, `description`, `model`, `tools` (array), `temperature`, `max_turns`, `timeout_mins`

Source: Claude Code docs / existing ADE templates in `src/ade/templates/agents/`.

### Hook substrate
- Wiring file: `.claude/settings.json` (or `~/.claude/settings.json` for user-level)
- Schema:
  ```json
  {
    "hooks": {
      "PreToolUse": [
        {
          "matcher": "Bash",
          "hooks": [{ "type": "command", "command": "script_path" }]
        }
      ]
    }
  }
  ```

Source: Claude Code docs.

### PreToolUse command field path
```
tool_input.command
```
For `Bash` tool calls the JSON envelope on stdin has `tool_input.command` containing the shell string.

Source: Claude Code docs; confirmed in existing `_hooklib.py.j2`.

### Model-tier identifiers
- Orchestrator: `claude-opus-4-5` (or current Opus release)
- Worker: `claude-sonnet-4-5`
- Fast/cheap: `claude-haiku-4-5`

Source: Anthropic model catalogue (these are label strings passed through unchanged by the harness).

---

## Gemini

### Skills dir(s)
Gemini CLI discovers skills in this precedence order (highest last):

| Tier | Primary path | Alias (higher precedence within same tier) |
|---|---|---|
| Built-in / Extension | (bundled) | — |
| User | `~/.gemini/skills/` | `~/.agents/skills/` |
| Workspace (project) | `.gemini/skills/` | `.agents/skills/` |

Within the same tier the **`.agents/skills/` alias takes precedence** over `.gemini/skills/`.
Each skill is a directory named after the skill, containing a `SKILL.md` file.

Source: https://geminicli.com/docs/cli/skills/

### Worker/subagent definition
- Directory (project): `.gemini/agents/`
- Directory (user): `~/.gemini/agents/`
- Extension: `.md`
- Frontmatter keys (YAML between `---` delimiters):
  - Required: `name` (lowercase, hyphens/underscores only), `description`
  - Optional: `kind` (`local` | `remote`), `model`, `tools` (array; supports wildcards), `mcpServers`, `temperature` (0.0–2.0), `max_turns` (default 30), `timeout_mins` (default 10)
- Body: becomes the agent's system prompt.

Source: https://geminicli.com/docs/core/subagents/

### Hook substrate
- Wiring file: `.gemini/settings.json` (project) or `~/.gemini/settings.json` (user)
- Merge order: project → user → system → extensions
- Schema:
  ```json
  {
    "hooks": {
      "BeforeTool": [
        {
          "matcher": "tool_name_pattern",
          "hooks": [
            {
              "name": "hook-id",
              "type": "command",
              "command": "script_path",
              "timeout": 5000
            }
          ]
        }
      ]
    }
  }
  ```
- Supported event types: `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `BeforeToolSelection`, `AfterModel`, `SessionStart`, `SessionEnd`, `Notification`, `PreCompress`
- Hooks communicate via stdin (JSON envelope) → stdout (JSON decision); stderr is for logs only.

Source: https://geminicli.com/docs/hooks/ and https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md

### PreToolUse command field path
**Event name: `BeforeTool`** (not `PreToolUse` — Gemini uses different naming).

Stdin envelope fields:
- `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp` (base fields)
- `tool_name` — tool being called
- `tool_input` — raw arguments object from the model
- `mcp_context` (optional), `original_request_name` (optional)

For bash/shell tool calls, the command string is at **`tool_input.command`** (inferred from the field
naming convention and the fact that file-write tools use `tool_input.content` / `tool_input.new_string`).

UNVERIFIED — The official docs confirm `tool_input` is "the raw arguments object" but do not
show a concrete JSON example for shell/bash tool calls. The path `tool_input.command` is a
best-guess default consistent with Claude's contract and the `.agents` interop convention; must
be confirmed by running a hook that dumps stdin during a Bash invocation.

Blocking output:
```json
{ "decision": "deny", "reason": "explanation sent to agent" }
```
Exit code `2` with stderr also blocks execution.

Source: https://geminicli.com/docs/hooks/reference/ and https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md

### Model-tier identifiers
Current active model strings (as of 2026-06):
- Orchestrator (Pro): `gemini-3.1-pro-preview` (also `gemini-2.5-pro` as fallback)
- Worker (Flash): `gemini-2.5-flash` (or `gemini-3-flash` when GA)

Note: Gemini 2.0 Flash was shut down 2026-06-01. Model IDs are specified in the `model` frontmatter
key of `.gemini/agents/*.md` files. If `model` is omitted, agents inherit the parent session model.

UNVERIFIED — exact current-GA identifiers for Gemini 3 are in preview (`gemini-3.1-pro-preview`);
best-guess fallbacks are `gemini-2.5-pro` and `gemini-2.5-flash` (both confirmed stable as of June 2026).

Source: https://geminicli.com/docs/get-started/gemini-3/ and https://ai.google.dev/gemini-api/docs/models

---

## Copilot

### Skills dir(s)
GitHub Copilot CLI discovers skills from these directories:

| Tier | Paths (all checked; no stated precedence order between them) |
|---|---|
| Project | `.github/skills/`, `.claude/skills/`, `.agents/skills/` |
| User | `~/.copilot/skills/`, `~/.agents/skills/` |

Each skill lives in its own subdirectory (e.g. `.github/skills/webapp-testing/`) containing a `SKILL.md`.
The `SKILL.md` must be named exactly `SKILL.md`; subdirectory names must be lowercase with hyphens.

UNVERIFIED — the documented precedence order between `.github/skills/`, `.claude/skills/`, and
`.agents/skills/` within the same project tier is not stated; best-guess default: Copilot treats
them as equivalent alternates and picks whichever exists.

Source: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills

### Worker/subagent definition
- Directory (project): `.github/agents/`
- Directory (user): `~/.copilot/agents/`
- Extension: `.agent.md`
- Frontmatter keys (YAML):
  - Required: `name`, `description`
  - Optional: `model` (e.g. `claude-opus-4-6`, `gpt-4.1`), `tools` (array), `handoffs`, `agents`, `target`, `user-invokable`, `argument-hint`
- Body: the agent's system prompt (max 30,000 characters).
- Precedence: user-level (`~/.copilot/agents/`) beats project-level (`.github/agents/`) on name conflict.

UNVERIFIED — exact complete YAML schema is not fully specified in the official docs. The keys above
are derived from multiple GitHub Docs pages and community references; treat as best-guess until
confirmed against the Copilot CLI source or a canonical schema page.

Source: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli and community guides.

### Hook substrate
- Wiring file: `.github/hooks/<name>.json` (project) or `~/.copilot/hooks/<name>.json` (user)
  - Policy (machine-wide): `/etc/github-copilot/policy.d/*.json`
- Schema:
  ```json
  {
    "version": 1,
    "disableAllHooks": false,
    "hooks": {
      "preToolUse": [
        {
          "type": "command",
          "matcher": "regex",
          "bash": "inline_script_or_path",
          "powershell": "windows_script",
          "command": "cross_platform_fallback",
          "cwd": "working_dir",
          "env": { "VAR": "VALUE" },
          "timeoutSec": 30
        }
      ]
    }
  }
  ```
- Supported CLI events (camelCase names): `sessionStart`, `sessionEnd`, `userPromptSubmitted`,
  `preToolUse`, `postToolUse`, `postToolUseFailure`, `permissionRequest`, `preCompact`, `agentStop`,
  `notification`, `errorOccurred`, `subagentStart`, `subagentStop`
- PascalCase aliases work too (`PreToolUse`, `SessionStart`, etc.) — field names shift to snake_case.
- **Fail-closed**: a crash or non-zero exit from a `preToolUse` hook denies the tool call.

Source: https://docs.github.com/en/copilot/reference/hooks-configuration and https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks

### PreToolUse command field path
Copilot ships **two naming conventions** for the same event:

| Event name in hooks.json | Payload field for tool name | Payload field for tool args | Command path |
|---|---|---|---|
| `preToolUse` (camelCase) | `toolName` | `toolArgs` (object) | `toolArgs.command` |
| `PreToolUse` (PascalCase) | `tool_name` | `tool_input` (object) | `tool_input.command` |

**IMPORTANT CONTRADICTION vs design assumption:**
The existing `_hooklib.py.j2` has `"copilot": lambda p: str(p.get("toolInput", {}).get("command", ""))`.
The verified docs show the camelCase variant uses **`toolArgs`** (not `toolInput`); PascalCase uses
`tool_input`. Neither uses `toolInput`. This is a bug in the current design default.

Recommended path for ADE: use the **PascalCase event** (`PreToolUse`) so the payload is
`tool_input.command` — matching Claude and Codex, simplifying `_ENVELOPE` to one shared lambda.

Blocking output:
```json
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "explanation",
  "modifiedArgs": {}
}
```

Source: https://docs.github.com/en/copilot/reference/hooks-configuration and https://docs.github.com/en/copilot/how-tos/copilot-sdk/hooks/pre-tool-use

### Model-tier identifiers
Models are specified via the `model` key in `.agent.md` frontmatter. Available in Copilot CLI (2026):
- Orchestrator: `claude-opus-4-6`, `gpt-5.5`, `gpt-4.1`
- Worker: `claude-sonnet-4-6`, `gpt-5.4-mini`, `gpt-4.1` (also marked "included" — no premium cost)
- Fast/cheap: `claude-haiku-4-5`, `gpt-5-mini`

UNVERIFIED — exact model ID strings for use in `.agent.md` `model:` frontmatter are not
confirmed in the official docs (docs show display names like "Claude Opus 4.6", not the API
identifier string). Use `/model` inside Copilot CLI to enumerate available IDs at runtime.

Source: https://docs.github.com/en/copilot/reference/ai-models/supported-models

---

## Codex

### Skills dir(s)
Codex discovers skills from these locations (lowest to highest precedence):

| Tier | Path |
|---|---|
| System | `/etc/codex/skills/` |
| User | `$HOME/.agents/skills/` |
| Project (repo root and parents) | `.agents/skills/` (scanned from CWD up to repo root) |

**Codex uses `.agents/skills/` exclusively** — it does NOT read a Codex-specific skills dir
(no `.codex/skills/`). The `.agents/skills/` path is the cross-harness interop standard.

Each skill is a directory containing a `SKILL.md`. Skills operate under a **discovery budget**:
Codex loads at most ~8,000 characters (≈2% of context window) of skill descriptions initially;
only `name` + `description` + file path are loaded at discovery. The full `SKILL.md` body is
injected only when the skill is selected (implicit match or explicit `/skills` invocation).

Source: https://developers.openai.com/codex/skills

### Worker/subagent definition
- Directory (project): `.codex/agents/`
- Directory (user): `~/.codex/agents/`
- Extension: `.toml` (one file per agent)
- Required TOML keys:
  - `name` — identifier Codex uses when spawning
  - `description` — guidance for when to deploy this agent
  - `developer_instructions` — core behavioral instructions (system prompt)
- Optional TOML keys:
  - `model` — inherits from parent if omitted
  - `model_reasoning_effort`
  - `sandbox_mode` — e.g. `"workspace-write"`, `"read-only"`
  - `mcp_servers`
  - `skills.config`
  - `nickname_candidates`

Source: https://developers.openai.com/codex/subagents

### Hook substrate
Hooks are discovered next to active config layers in either form:
- `~/.codex/hooks.json` or `<repo>/.codex/hooks.json` (JSON file)
- Inline `[hooks]` tables inside `~/.codex/config.toml` or `<repo>/.codex/config.toml`

JSON schema:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Bash$",
        "hooks": [
          {
            "type": "command",
            "command": "script_path",
            "timeout": 30,
            "statusMessage": "optional"
          }
        ]
      }
    ]
  }
}
```

TOML equivalent:
```toml
[[hooks.PreToolUse]]
matcher = "^Bash$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = '/usr/bin/python3 "script_path"'
timeout = 30
statusMessage = "Checking..."
```

Supported event types: `SessionStart`, `SubagentStart`, `PreToolUse`, `PermissionRequest`,
`PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`

Source: https://developers.openai.com/codex/hooks

### PreToolUse command field path
```
tool_input.command
```
Codex uses snake_case identical to Claude. `Bash` and `apply_patch` tool calls carry the shell
string at `tool_input.command`. MCP tool calls follow the same envelope shape.

Blocking output (primary):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "reason text"
  }
}
```
Legacy alternative: `{ "decision": "block", "reason": "..." }`. Exit code `2` also blocks.

Source: https://developers.openai.com/codex/hooks

### Model-tier identifiers
Codex model strings (as of 2026-06):
- Orchestrator: `gpt-5.5` (flagship), `gpt-5.4` (professional fallback)
- Worker/subagent: `gpt-5.4-mini` (fast, efficient for spawned subagents)
- Research preview: `gpt-5.3-codex-spark` (ChatGPT Pro only; near-instant iteration)

Deprecated (do not use): `gpt-5.2`, `gpt-5.3-codex`

Specified via `model` key in `.codex/agents/*.toml` or via `--model`/`-m` CLI flag,
or `model = "..."` in `config.toml`.

Source: https://developers.openai.com/codex/models

---

## Cross-harness Summary

| Harness | Skills dir (project) | Worker def dir / ext | Hook wiring file | PreToolUse event name | Command field path |
|---|---|---|---|---|---|
| Claude | `.claude/skills/` | `.claude/agents/*.md` | `.claude/settings.json` | `PreToolUse` | `tool_input.command` |
| Gemini | `.gemini/skills/` or `.agents/skills/`¹ | `.gemini/agents/*.md` | `.gemini/settings.json` | `BeforeTool`² | `tool_input.command`³ |
| Copilot | `.github/skills/` or `.claude/skills/` or `.agents/skills/` | `.github/agents/*.agent.md` | `.github/hooks/<name>.json` | `PreToolUse` (PascalCase) | `tool_input.command`⁴ |
| Codex | `.agents/skills/` | `.codex/agents/*.toml` | `.codex/hooks.json` or `config.toml [hooks]` | `PreToolUse` | `tool_input.command` |

¹ `.agents/skills/` has higher precedence within the same tier.
² Gemini uses `BeforeTool` not `PreToolUse` — different event name.
³ UNVERIFIED: `tool_input.command` is best-guess for bash tools; docs confirm `tool_input` is the args object but don't show a bash example.
⁴ Use PascalCase `PreToolUse` event to get `tool_input` (snake_case payload); camelCase `preToolUse` yields `toolArgs`, not `toolInput`.

### Key contradiction vs prior design assumption
`_hooklib.py.j2` line 103 uses `p.get("toolInput", {})` for Copilot. The verified docs show
neither convention uses `toolInput` — camelCase uses `toolArgs`, PascalCase uses `tool_input`.
**C1 must fix this**: change Copilot to PascalCase `PreToolUse` + `tool_input.command`.
