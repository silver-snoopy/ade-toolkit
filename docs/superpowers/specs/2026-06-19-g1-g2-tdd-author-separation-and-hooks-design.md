# Design — G1 + G2: Author-separated TDD & a deterministic hook layer

**Date:** 2026-06-19
**Status:** Approved (design); pending implementation plan
**Scope:** ADE toolkit (`src/ade/`) — closes gaps G1 and G2 from `docs/ade-sdlc-gap-analysis.html`.

## 1. Context & motivation

The ADE-vs-field gap analysis identified five structural gaps in ADE's development
core. This design closes the two highest-leverage ones:

- **G1 — No author separation in implementation.** ADE's Phase 4 currently has a
  single subagent write *both* the implementation and its tests in one pass
  (`04-implement.md`: "Write unit tests alongside the implementation"). This is the
  field's documented #1 silent-failure mode: the model rewrites the test to match
  whatever code it produced. Seven of nine surveyed systems make implementation
  test-first; the strongest (LeRisque, case) make it *author-separated* —
  the agent that writes the failing test is structurally distinct from the agent
  that writes the code to green.

- **G2 — No deterministic enforcement layer.** ADE runs mechanical checks through a
  Haiku `test-runner` subagent, spending model tokens (and inheriting LLM
  non-determinism) on checks that should be a hard, deterministic gate. The research
  is explicit that defense-in-depth needs at least one enforcement layer whose
  verdict does not depend on LLM reasoning.

These two are coupled: **G1's enforcement mechanism is the first hook in G2's layer.**

### Design constraint from the operator

The hook layer must work with **GitHub Copilot and Claude Code interchangeably**.
This is satisfied by an **install-mode selector** chosen at `ade init` time: the same
deterministic check *scripts* are always emitted, but their *wiring* (what triggers
them) adapts to the target agent.

## 2. Goals / non-goals

**Goals**
- Split Phase 4 into a test-writer step and a separate implementer step, with a
  structural author-separation invariant.
- Add two deterministic check scripts (the "Core two" set) that reject the two
  failure modes ADE is most exposed to: mixed test+impl commits, and committed stubs.
- Make hook wiring agent-selectable at init: `--agent claude` (default) emits Claude
  Code `settings.json` hooks; `--agent copilot` emits a git `pre-commit` config.
- Keep all check logic in single shared scripts that work under both substrates.

**Non-goals (explicitly deferred)**
- G3 (compounding retro), G4 (blast-radius routing), G5 (collapse the
  `backend-coder`/`frontend-coder` agents into one language-agnostic implementer;
  de-hardcode the JS/TS stack).
- A `both` or `none` install mode (only `claude` and `copilot` for now).
- Full cross-harness skill emission. `--agent` today affects **only hook wiring**.
- Broadening the hook set beyond the Core two (silent-catch, file-budget, etc. are
  future additions).

## 3. Design

### 3.1 Phase 4 redesign — test-writer → implementer

Phase 3 (Design Check / stubs) is **retained**. Stubs are what make test-first cheap:
they give the test-writer real signatures to import and assert against. The new Phase 4
runs two ordered sub-steps inside the existing worktree:

**4a — Test-writer** (new agent `test-writer`, Sonnet)
- Input: the spec's acceptance criteria + the Phase-3 stub signatures.
- Writes *failing* tests. Owns **test files only**.
- Runs the suite and confirms it is RED (tests fail because logic is unimplemented,
  not because of import/collection errors).
- Commits a **test-only** commit: `test: add failing tests for <task-id>`.

**4b — Implementer** (existing `backend-coder` / `frontend-coder`, Sonnet)
- Input: the spec, the **committed failing tests**, and the stubs — **not** the
  test-writer's reasoning.
- Writes the minimum code to turn the suite green. **Forbidden from creating or
  editing test files.**
- Commits an **impl-only** commit: `feat: …` / `fix: …`.
- Build-order rule (shared → backend → frontend) and file-ownership rules are
  unchanged from the current Phase 4.

**Author-separation invariant (new orchestrator rule)**
> The orchestrator dispatches the implementer (4b) without passing the test-writer's
> reasoning or narrative. The implementer sees only the spec, the failing tests on
> disk, and the stubs. Because 4a and 4b are separate subagent dispatches, their
> contexts are already disjoint; this invariant makes that a guarantee rather than an
> accident.

This invariant is added to `docs/ade-architecture-design.md` ("Orchestrator
invariants") and to the Phase 4 skill.

### 3.2 The check scripts (G2 "Core two")

Two Python scripts, language-agnostic, emitted to the **version-controlled**
`.ade/hooks/` directory (`.ade/.gitignore` ignores only `tasks/` and `worktrees/`,
so `hooks/` is committed — this is required so the checks run for Copilot, CI, and
humans, not just locally).

**`block-mixed-commit.py`** — G1's structural enforcer.
- Collects the changed source files (see 3.4 for how inputs arrive per substrate).
- Classifies each as *test* or *non-test* via a path-pattern table:
  `*_test.*`, `test_*.*`, `*.test.*`, `*.spec.*`, and any path segment in
  `{__tests__, tests, test, spec, specs, e2e}`.
- **Rejects** (non-zero exit) if the changed set contains *both* a test file and a
  non-test source file.
- **Escape hatch:** a `[test-refactor]` marker in the commit message allows a mixed
  commit (mirrors LeRisque; for the legitimate refactor-tests-with-code case).

**`check-leftover-stub.py`** — guards ADE's stub-first risk.
- Scans changed **non-test** source files for unfilled stub markers:
  `NotImplementedError`, `Not implemented`, `TODO: implement`, `FIXME: implement`,
  `throw new Error\(['"]Not implemented`, `todo!\(\)` (Rust), `unimplemented!\(\)`.
- **Rejects** if any changed non-test source file still contains one. (Phase 3 stubs
  are expected to contain these; this hook ensures they are *gone* by the time
  implementation is committed.)

Both scripts:
- Operate on changed files only (not the whole tree), so they are fast and scoped.
- Use **exit codes** as the universal signal: `0` = pass, non-zero = reject. Both
  substrates agree on this (pre-commit: non-zero fails the commit; Claude Code:
  exit `2` blocks the tool call and surfaces stderr).
- Print a clear, actionable message to stderr naming the offending files and the rule.

### 3.3 Install-mode selector

`ade init` gains `--agent {claude, copilot}` (default `claude`).

| Mode | Wiring artifact emitted | Trigger | Install step |
|---|---|---|---|
| `claude` *(default)* | `.claude/settings.json` hooks | Claude tool loop: PreToolUse on `Bash` matching `git commit` | none |
| `copilot` | `.pre-commit-config.yaml` (repo root) | any `git commit` (Copilot, CI, human) | `pre-commit install` |

**Both checks fire at commit time in both modes** — they scan the *staged* file set.
This is deliberate: stubs written in Phase 3 are legitimate until the implementation
commit, so a write/edit-time stub check would wrongly block Phase 3. Anchoring both
hooks to the commit boundary also makes the two substrates semantically identical
(same checks, same staged-file inputs, same exit-code contract).

The `.ade/hooks/*.py` scripts are emitted in **both** modes; only the wiring differs.
Rationale for `claude` default: it is the zero-install "starter" the operator
requested. `copilot` is the agent-agnostic git backstop and is opt-in.

### 3.4 One script, two invocation modes

Both checks fire at commit time and scan the **staged** file set; each script adapts to
its caller so the core logic is written once:

- **git / pre-commit:** the framework passes staged filenames as argv. If argv is
  empty, the script falls back to `git diff --cached --name-only`. The commit message
  (for the `[test-refactor]` marker) is read from `$PRE_COMMIT_COMMIT_MSG_FILENAME` /
  `.git/COMMIT_EDITMSG` when available.
- **Claude Code hook:** the PreToolUse payload arrives as JSON on stdin. The script
  confirms the `Bash` command is a `git commit`, extracts any `-m` message (for the
  `[test-refactor]` marker), then inspects `git diff --cached`. Exits `2` to block.

Mode is detected by: presence of stdin JSON with a `tool_input` → Claude mode;
otherwise → git mode (argv or `git diff --cached`). A small shared helper (`_hooklib`)
holds the file-classification patterns, the stub patterns, the staged-file/message
gathering, and the exit-code contract so both scripts stay thin. The helper is emitted
alongside the scripts in `.ade/hooks/`.

### 3.5 Idempotent wiring emission

- **`.claude/settings.json` (claude mode):** commonly pre-exists (permissions, env).
  ADE **merges**: parse existing JSON, insert the ADE hook entries keyed by their
  `.ade/hooks/...` command so re-running `ade init` does not duplicate them, write
  back. If the file is absent, create it. Hooks ADE manages are recognizable by their
  command path, making the merge idempotent.
- **`.pre-commit-config.yaml` (copilot mode):** YAML merge is fragile, so this is
  **seed-if-missing** (user-owned, like `CONTEXT.md`). If it already exists, ADE does
  not modify it and instead prints the exact `repo: local` block to paste, plus the
  `pre-commit install` reminder.

### 3.6 CLI, doctor, and docs

- **`cli.py`:** add the `--agent` option; render `.ade/hooks/` (always); emit/merge
  the mode-specific wiring artifact; print what was created/merged/kept.
- **`doctor`:** mode-aware. Detect whichever wiring file exists; verify the
  `.ade/hooks/*.py` scripts are present; if `.pre-commit-config.yaml` exists, nudge
  `pre-commit install` (the `pre-commit` optional-tool check already exists).
- **Docs:** update `docs/ade-architecture-design.md` (Phase 4 description, subagent
  catalog +`test-writer`, orchestrator invariants +author-separation, circuit-breaker
  table) and `claude_md_section.md.j2` (Phase 4 summary).

## 4. Files touched

**New templates**
- `agents/test-writer.md.j2`
- `hooks/_hooklib.py.j2` (shared patterns + input gathering)
- `hooks/block-mixed-commit.py.j2`
- `hooks/check-leftover-stub.py.j2`
- `claude_settings.json.j2` (claude-mode wiring; merged at init)
- `pre-commit-config.yaml.j2` (copilot-mode wiring; seed-if-missing)

**Edited templates**
- `skills/phases/04-implement.md.j2` — rewrite to test-writer → implementer.
- `skills/ade-code.md.j2`, `skills/ade-full.md.j2` — phase wiring + invariant.
- `agents/backend-coder.md.j2`, `agents/frontend-coder.md.j2` — add "never create or
  edit test files" rule; relabel as implementers.
- `claude_md_section.md.j2` — Phase 4 summary.

**Source**
- `src/ade/cli.py` — `--agent` option, hook rendering, settings.json merge helper,
  seed-if-missing pre-commit config, doctor updates.

**Docs**
- `docs/ade-architecture-design.md` — Phase 4, subagent catalog, invariants, breakers.

**Tests** (`tests/`)
- `block-mixed-commit`: rejects mixed, passes test-only, passes impl-only, honors
  `[test-refactor]`, handles new-file-only and docs-only no-ops.
- `check-leftover-stub`: rejects each stub marker in non-test source, ignores stubs in
  test files, passes clean impl.
- Both scripts under git-argv invocation and Claude-stdin invocation.
- `cli.py`: `--agent claude` emits/merges `settings.json`; `--agent copilot` seeds
  `.pre-commit-config.yaml`; both emit `.ade/hooks/`; settings.json merge is
  idempotent across two inits; pre-commit config seed-if-missing preserves an existing
  file.

## 5. Edge cases & circuit breakers

- **Test-writer cannot make tests RED** (e.g. a trivial one-line change with no
  meaningful behavior to assert): note it and proceed; the author separation still
  holds (implementer is still a separate dispatch).
- **Implementer repeatedly fails to green:** the existing Phase 5 fixer loop (max 3)
  applies. If a fix genuinely requires a test change, it is a **separate** commit
  (or uses the `[test-refactor]` marker), never a silent in-place test rewrite.
- **New-file-only or docs-only change:** `block-mixed-commit` is a no-op unless both
  a test and a non-test source file are present; `check-leftover-stub` scans source
  files only. Trivial-change routing is **G4**, out of scope here.
- **Project with no test framework:** the test-writer creates the first test file and
  the convention takes hold; the hooks remain valid (they classify by path, not by a
  runner being configured).
- **Hook false positives:** the stub-pattern list is conservative and source-only;
  the `[test-refactor]` marker is the documented escape for the one legitimate
  mixed-commit case. No silent bypass exists otherwise.

## 6. Rollout / compatibility

- Default `--agent claude` means existing zero-config users get the Claude wiring with
  no new install step.
- Re-running `ade init` is idempotent: scripts are regenerated (ADE-owned), the
  settings.json merge does not duplicate, and an existing `.pre-commit-config.yaml` is
  preserved.
- No change to the Phase 1–3 / 5–10 contracts beyond Phase 4's internal split and the
  doctor/catalog/doc updates.

## 7. Open questions

None blocking. (Future: a `both` mode, a broader hook set, and wiring the same
selector into a real cross-harness emission are tracked under G3/G4/G5 and later
work.)
