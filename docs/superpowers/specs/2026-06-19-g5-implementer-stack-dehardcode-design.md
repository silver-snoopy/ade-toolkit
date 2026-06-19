# Design — G5: Language-agnostic implementer, stack de-hardcoding, remove live verification

**Date:** 2026-06-19
**Status:** Approved (design); pending implementation plan
**Scope:** ADE toolkit (`src/ade/`) — closes gap G5 from `docs/ade-sdlc-gap-analysis.html`, plus the operator-directed removal of live verification from the pipeline.

## 1. Context & motivation

The gap analysis flagged that ADE's dev phases, while claiming portability, hardcode a JS/TS monorepo: `@vitals/*` package names, `npm run build -w`, a fixed `shared → backend → frontend` build order, and a Phase 7 that depends on `docker compose` + Playwright + `localhost`. Every stack-agnostic competitor externalizes stack commands into detected/config files. G5 makes ADE genuinely stack-neutral.

Three coupled changes:
- **G5a — One implementer:** collapse `backend-coder` + `frontend-coder` (layer/language-named agents) into a single language-agnostic `implementer`. The 2025–26 consensus is that a single coder + good context + a TDD discipline beats language-named agents; the split was a portability liability.
- **G5b — Stack commands as data:** replace hardcoded build/lint/format/test/dev commands with a detected, committed, user-editable `.claude/ade-stack.md`, referenced generically by the phase skills.
- **G5c — Remove live verification (operator directive):** delete Phase 7 (post-implementation live verify) and the pre-implementation bug-reproduction step (`qa-verify-bug`). Both depend on docker/Playwright/localhost — the most stack-coupled parts of the pipeline. With G1's author-separated TDD already shipped, the test suite is the acceptance mechanism.

## 2. Goals / non-goals

**Goals**
- A single `implementer` agent replaces both coder agents; all references updated.
- A detected, committed `.claude/ade-stack.md` holds build/lint/format/test/dev commands; phases reference it instead of hardcoding npm/@vitals.
- The fixed `shared → backend → frontend` build order generalizes to "dependencies before dependents; the plan's task DAG defines the order."
- Phase 7 (live verify) and `qa-verify-bug` are removed; phases renumber to a clean `0–9`; acceptance is verified by the TDD suite + a Phase-6 coverage gate.
- All affected tests updated; the suite stays green.

**Non-goals (deferred)**
- G4 (blast-radius routing) and G3 (compound loop) — separate cycles after this one.
- Any replacement live-verification or smoke step — by operator directive, tests are the acceptance mechanism; nothing live remains in the loop.
- Auto-detecting commands for stacks `detect.py` doesn't already know (python, javascript, typescript, go, rust) — unknown stacks get commented placeholders the user fills in.
- Re-detecting/overwriting `.claude/ade-stack.md` on re-init (it is seed-if-missing, user-owned thereafter).

## 3. Design

### 3.1 G5a — the `implementer` agent

New `src/ade/templates/agents/implementer.md.j2` (frontmatter `model: sonnet`, tools `[Read, Write, Edit, Bash, Glob, Grep]`). Body (language-agnostic, preserves the G1 implementer contract):

- Makes the test-writer's FAILING tests pass with the minimum correct implementation.
- Follows project conventions in CLAUDE.md and `.claude/ade-stack.md`.
- Only edits files assigned to it; never creates or edits test files (the `block-mixed-commit` hook enforces this).
- Leaves no stub markers in committed source (`check-leftover-stub` enforces this).
- Runs the project's build + test commands (from `.claude/ade-stack.md`) to confirm GREEN.
- Commits implementation as its own commit (`feat:` / `fix:`).

`backend-coder.md.j2` and `frontend-coder.md.j2` are **deleted**. Because `cli.py` renders agents by globbing `agents/*.j2`, deletion is automatic — no cli change needed for that. Parallel implementation (multiple non-overlapping units) is expressed by dispatching multiple `implementer` instances with disjoint file assignments — the existing "no two agents edit the same file" rule still governs.

### 3.2 G5b — `.claude/ade-stack.md` + `detect.py`

**Template** `src/ade/templates/stack.md.j2` renders to `.claude/ade-stack.md` (seed-if-missing). Content:
```markdown
# ADE stack commands

ADE phase skills read this file for the project's commands. `ade init` seeds it from
stack detection; edit any line to correct it. One block per detected language.

## <language>
- build:  <command or "# set your build command">
- lint:   <command>
- format: <command>
- test:   <command>
- dev:    <command>
```

**`detect.py`** gains command maps mirroring the existing `_DEFAULT_TEST_COMMANDS`:
- `_DEFAULT_BUILD_COMMANDS`, `_DEFAULT_LINT_COMMANDS`, `_DEFAULT_FORMAT_COMMANDS`, `_DEFAULT_DEV_COMMANDS` keyed by language.
  - python → build `""` (none) / lint `ruff check` / format `ruff format` / test `pytest --tb=short -q` / dev `""`.
  - javascript/typescript → build `npm run build` / lint `npm run lint` / format `npm run format` / test (existing detection, default `npm test`) / dev `npm run dev`.
  - go → build `go build ./...` / lint `go vet ./...` / format `gofmt -l .` / test `go test ./...` / dev `""`.
  - rust → build `cargo build` / lint `cargo clippy` / format `cargo fmt --check` / test `cargo test` / dev `""`.
- `ProjectInfo` gains a `commands: dict[str, dict[str, str]]` field — `{language: {build, lint, format, test, dev}}` — populated by a new `_detect_commands` step that reuses the existing package.json `scripts.test` override logic for the test slot. Empty/unknown slots render as a `# set your <slot> command` placeholder so the file is always actionable.

The `cli.py` `init` seeds the file: `_render_and_write_if_missing(env, "stack.md.j2", project_dir / ".claude" / "ade-stack.md", ctx)`, with a created/kept print line. (Placed with the other seed-if-missing bootstrap artifacts, but under `.claude/` since it is ADE-tooling config, not a user doc.)

### 3.3 G5b — phase skill de-hardcoding

Across `02-plan`, `03-design-check`, `04-implement`, `05-quality-gate`, `ade-full`, `ade-code`:
- Remove `@vitals/*`, `packages/backend|frontend|shared`, `npm run build -w …`, `npm run lint|format:check|test|test:e2e`, `import type`, Prettier/4-space-Java specifics.
- Replace command references with: *"run the project's `<build|lint|format|test>` command (see `.claude/ade-stack.md`)."*
- Replace the build-order rule everywhere with: **"Build dependencies before dependents. The plan's ordered task list / DAG defines the order — there is no fixed package order."**
- `03-design-check` stub examples become language-neutral prose describing *what* a stub is (type/signature/throw-or-raise placeholder) rather than TypeScript snippets.
- `02-plan`'s example file table and task list become generic (no `packages/...`), illustrating the *structure* (CREATE/MODIFY rows, dependency-ordered tasks) without a specific stack.
- Convention guidance defers to CLAUDE.md + `.claude/ade-stack.md` rather than enumerating TS/Java rules.

### 3.4 G5c — remove live verification + renumber

- **Delete** `skills/phases/07-verify.md.j2` and `skills/phases/qa-verify-bug.md.j2`.
- **`ade-full.md.j2`:** remove the `## Phase 7 — VERIFY` section and the `## QA VERIFY (bugs only …)` block; update the Pipeline Overview diagram (drop both); remove the `Verify→review reject` circuit breaker; renumber subsequent phases.
- **Renumber** phase files and all references to a clean sequence:
  - `08-docs.md.j2` → `07-docs.md.j2`
  - `09-ship.md.j2` → `08-ship.md.j2`
  - `10-retro.md.j2` → `09-retro.md.j2`
  - Update every `Phase N` heading, every `Phase N/10` status string → `Phase N/9`, and the `[phases/NN-….md]` links inside `ade-full.md.j2`.
- **`10-retro` (→ `09-retro`):** remove the `verify` entries from `cycleTime.phases` and `iterations` (`verifyRejectCycles`), and the verify-related task-dir artifacts (`verification/` block). Keep cycle metrics for the remaining phases.
- **Acceptance-by-tests:**
  - `00-intent.md.j2` already requires testable criteria — add one line: "Each criterion must be expressible as an automated test (the Phase-4 test-writer will pin each to a test)."
  - `04-implement.md.j2` (4a): add "Map each Phase-0 acceptance criterion to at least one test."
  - `06-review.md.j2`: add an **acceptance-coverage gate** — "Confirm every Phase-0 acceptance criterion has a covering test; a criterion with no test is an Important finding." This replaces live evidence as the acceptance check.
- **Circuit breakers** (in `ade-full` + architecture doc): drop the `Verify→review reject` row.

### 3.5 Documentation

`docs/ade-architecture-design.md`:
- 10-phase table → 9-phase (0–9): drop the Verify row; renumber Docs/Ship/Retro; update the Phase 4 actor to `test-writer (RED) → implementer (GREEN)` (single implementer).
- Subagent catalog: replace `backend-coder`/`frontend-coder` rows with one `implementer` row.
- Update the human-gates line: the merge gate moves from "after Phase 9" to "after Phase 8 (Ship)" due to renumbering (Phase 7 verify had no dedicated human gate, so none is removed — only the gate's phase number shifts).
- Circuit-breaker table: drop the verify row.
- Add a short "Stack configuration (`.claude/ade-stack.md`)" subsection.
- Update the "Phases 2–10" heading/section to "Phases 2–9" and its Phase 4/7/8 bullets.

## 4. Files touched (summary)

**New:** `agents/implementer.md.j2`, `stack.md.j2`.
**Deleted:** `agents/backend-coder.md.j2`, `agents/frontend-coder.md.j2`, `skills/phases/07-verify.md.j2`, `skills/phases/qa-verify-bug.md.j2`.
**Renamed:** `skills/phases/08-docs.md.j2`→`07-docs.md.j2`, `09-ship`→`08-ship`, `10-retro`→`09-retro`.
**Edited:** `detect.py`, `cli.py`, `02-plan`, `03-design-check`, `04-implement`, `05-quality-gate`, `06-review`, `ade-full.md.j2`, `ade-code.md.j2`, `claude_md_section.md.j2`, `00-intent.md.j2`, `docs/ade-architecture-design.md`.

## 5. Tests

**Update:**
- `test_init_python_project`: assert `implementer.md` exists; drop `backend-coder.md` assertion (or assert it's absent).
- `test_init_agent_definitions_have_model`: read `implementer.md` instead of `backend-coder.md`.
- `test_init_generates_phase_docs`: assert `07-verify.md` and `qa-verify-bug.md` are ABSENT; assert the renamed docs/ship/retro phase files exist (`07-docs.md`, `08-ship.md`, `09-retro.md`).
- `test_init_skills_have_phase_content`: `Phase 10`/`RETROSPECTIVE` assertion → `Phase 9`/`RETROSPECTIVE`.
- **Remove** `test_init_full_skill_has_live_verification` (the "NO EXEMPTIONS" live-verify guarantee is intentionally gone).

**Add:**
- `test_init_generates_implementer_agent` (exists, model sonnet, "never … test files", language-agnostic — no `@vitals`/`import type`).
- `test_init_seeds_ade_stack_file` (`.claude/ade-stack.md` exists, contains `build:`/`lint:`/`test:`, seed-if-missing preserves an existing edited file).
- `test_init_no_live_verification` (neither `07-verify.md` nor `qa-verify-bug.md` rendered; `ade-full.md` contains no `Playwright`/`docker compose`/`localhost` references).
- `test_detect_commands` (in `tests/test_detect.py`): a python project yields `ruff`/`pytest` commands; a node project yields `npm` commands.

**Verify no stale references:** grep the generated `.claude/` tree for `@vitals`, `npm run … -w`, `backend-coder`, `frontend-coder`, `Playwright`, `Phase 7`, `/10` — none should remain except where intentionally generic.

## 6. Edge cases

- **Multi-language repo:** `ade-stack.md` lists one block per detected language; phases say "run the relevant language's command."
- **Unknown/undetected stack:** every command slot renders a `# set your <slot> command` placeholder — the file is still valid and actionable; nothing crashes.
- **User edited `ade-stack.md` then re-runs init:** seed-if-missing preserves their file (prints `= Kept existing`).
- **A project that genuinely wants live/browser checks:** out of scope by directive; the user can add their own verification outside the ADE loop.
- **Renumber collisions:** rename in dependency-safe order (highest number first: 10→09, 09→08, 08→07) to avoid clobbering.

## 7. Rollout / compatibility

- Existing ADE projects re-running `ade init` get the new `implementer` agent and `ade-stack.md`; the deleted coder/verify files are simply no longer regenerated (stale copies, if any, can be removed by the user — `ade doctor` is not currently asked to flag them; out of scope).
- The pipeline contract changes (no Phase 7, renumbered tail). This is a deliberate, operator-approved breaking change to the workflow shape.

## 8. Open questions

None blocking. (Future: `ade doctor` could warn on stale `backend-coder.md`/`07-verify.md` from a pre-G5 init; deferred.)
