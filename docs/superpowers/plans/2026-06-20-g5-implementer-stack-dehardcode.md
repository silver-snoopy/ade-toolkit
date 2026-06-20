# G5 — Language-agnostic implementer, stack de-hardcoding, remove live verification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ADE genuinely stack-neutral — collapse the two layer-named coder agents into one `implementer`, move build/lint/format/test commands into a detected, user-owned `.claude/ade-stack.md`, and remove the docker/Playwright/localhost live-verification phase so the TDD suite is the acceptance mechanism.

**Architecture:** ADE has no runtime — `ade init` (Python/Typer + Jinja2) renders Markdown agent/skill/command templates into a target project's `.claude/` tree. This plan is almost entirely (a) two small Python changes in `detect.py`/`cli.py` plus (b) edits to Jinja2 `.j2` templates and the architecture doc. Every change is validated by `pytest` assertions over the generated tree.

**Tech Stack:** Python 3.11+, Typer, Jinja2, Rich, pytest, ruff. Templates under `src/ade/templates/`. Tests under `tests/`.

## Global Constraints

- Python 3.11+; type hints on all public functions; ruff line-length 99.
- Tests in `tests/` mirror `src/`. Run `pytest` (all) and `ruff check src/ tests/` before each commit; both must be clean.
- Conventional commits.
- User-owned, seed-if-missing artifacts are never overwritten — `.claude/ade-stack.md` joins this class (use `_render_and_write_if_missing`).
- The Jinja env uses `trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True` — author `.j2` control blocks accordingly.
- `cli.py` renders agents/skills/commands by globbing template dirs, so deleting a `.j2` file removes it from output with no cli change. Hook scripts and explicit seeds are the exceptions.
- The literal string `Phase 7` is **allowed** after renumbering (it denotes Docs). Forbidden stale tokens (must not appear anywhere in the generated `.claude/` tree or generated `CLAUDE.md` section): `@vitals`, `-w @`, `backend-coder`, `frontend-coder`, `Playwright`, `docker compose`, `localhost`, `NO EXEMPTIONS`, `07-verify`, `qa-verify`, `/10`.
- Source spec: `docs/superpowers/specs/2026-06-19-g5-implementer-stack-dehardcode-design.md`. Where this plan and the spec disagree, the spec wins — except the two spec gaps explicitly called out in Task 9 / Task 12.

---

## File Structure

**New files**
- `src/ade/templates/agents/implementer.md.j2` — the single language-agnostic implementer agent (G5a).
- `src/ade/templates/stack.md.j2` — renders to `.claude/ade-stack.md` (G5b).

**Deleted files**
- `src/ade/templates/agents/backend-coder.md.j2`, `src/ade/templates/agents/frontend-coder.md.j2`
- `src/ade/templates/skills/phases/07-verify.md.j2`, `src/ade/templates/skills/phases/qa-verify-bug.md.j2`

**Renamed files** (rename highest-number-first to avoid clobbering — spec §6)
- `skills/phases/10-retro.md.j2` → `09-retro.md.j2`
- `skills/phases/09-ship.md.j2` → `08-ship.md.j2`
- `skills/phases/08-docs.md.j2` → `07-docs.md.j2`

**Edited files**
- Code: `src/ade/detect.py`, `src/ade/cli.py`
- Phase detail skills: `00-intent`, `02-plan`, `03-design-check`, `04-implement`, `05-quality-gate`, `06-review` (and the three renamed tail files)
- Composite skills: `skills/ade-full.md.j2`, `skills/ade-code.md.j2`, `skills/ade-review.md.j2`, `skills/ade-ship.md.j2`, `skills/ade-pr-review.md.j2`
- Command wrapper: `commands/ade_review.md.j2`
- `src/ade/templates/claude_md_section.md.j2`
- `docs/ade-architecture-design.md`
- Tests: `tests/test_cli.py`, `tests/test_detect.py`

---

## Task 1: The single `implementer` agent (G5a)

**Files:**
- Create: `src/ade/templates/agents/implementer.md.j2`
- Delete: `src/ade/templates/agents/backend-coder.md.j2`, `src/ade/templates/agents/frontend-coder.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: a rendered `.claude/agents/implementer.md` (model `sonnet`); removes `.claude/agents/backend-coder.md` and `.claude/agents/frontend-coder.md`. Later tasks refer to the implementer by the agent name `implementer`.

- [ ] **Step 1: Update the existing tests that reference the coder agents (write the failing tests first)**

In `tests/test_cli.py`, change line 18 inside `test_init_python_project` from:

```python
    assert (python_project / ".claude" / "agents" / "backend-coder.md").exists()
```
to:
```python
    assert (python_project / ".claude" / "agents" / "implementer.md").exists()
```

Replace `test_init_agent_definitions_have_model` (lines 69–78) body so it reads `implementer.md`:

```python
def test_init_agent_definitions_have_model(python_project: Path) -> None:
    """Agent definitions should specify a model."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    implementer = (python_project / ".claude" / "agents" / "implementer.md").read_text()
    assert "model:" in implementer
    assert "sonnet" in implementer

    test_runner = (python_project / ".claude" / "agents" / "test-runner.md").read_text()
    assert "haiku" in test_runner
```

Replace `test_coders_forbidden_from_test_files` (lines 288–291) with an implementer-named version plus a new dedicated test:

```python
def test_implementer_forbidden_from_test_files(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    impl = (python_project / ".claude" / "agents" / "implementer.md").read_text()
    assert "test file" in impl.lower()


def test_init_generates_implementer_agent(python_project: Path) -> None:
    """A single language-agnostic implementer replaces the two coder agents."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents = python_project / ".claude" / "agents"
    impl = agents / "implementer.md"
    assert impl.exists()
    content = impl.read_text()
    assert "model:" in content and "sonnet" in content
    assert "test file" in content.lower()
    # Language-agnostic: no hardcoded JS/TS stack leaks in.
    assert "@vitals" not in content
    assert "import type" not in content
    # The old layer-named coders are gone.
    assert not (agents / "backend-coder.md").exists()
    assert not (agents / "frontend-coder.md").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cli.py::test_init_generates_implementer_agent tests/test_cli.py::test_init_python_project -v`
Expected: FAIL — `implementer.md` does not exist yet; `backend-coder.md` still exists.

- [ ] **Step 3: Create the implementer template**

Create `src/ade/templates/agents/implementer.md.j2`:

```markdown
---
model: sonnet
tools: [Read, Write, Edit, Bash, Glob, Grep]
---
You are an implementer working in a git worktree. You make the test-writer's FAILING
tests pass by writing the minimum correct implementation. You are language-agnostic:
the project's stack, conventions, and commands come from CLAUDE.md and
`.claude/ade-stack.md` — never assume a specific language, framework, or package layout.

Rules:
- Make the failing tests pass with the minimum correct implementation.
- Follow the project's conventions in CLAUDE.md and the commands in `.claude/ade-stack.md`.
- Only edit files assigned to you — never touch files outside your assignment. When work
  is split across multiple implementers, no two agents may edit the same file.
- NEVER create or edit test files. Tests are owned by the test-writer; the
  `block-mixed-commit` hook rejects commits that mix tests with implementation. If a test
  looks wrong, report it to the orchestrator rather than editing it.
- Replace every stub: no `Not implemented` / `NotImplementedError` / `TODO: implement`
  may remain in source you commit (the `check-leftover-stub` hook enforces this).
- Use Edit for existing files, Write only for new files.
- Run the project's build and test commands (from `.claude/ade-stack.md`) to confirm the
  suite is GREEN. If a command is `none` or unset, skip that step.
- Commit implementation as its own commit: `feat:` / `fix:`.
```

- [ ] **Step 4: Delete the two coder templates**

```bash
git rm src/ade/templates/agents/backend-coder.md.j2 src/ade/templates/agents/frontend-coder.md.j2
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_cli.py -v -k "implementer or agent_definitions or python_project"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/agents/implementer.md.j2 tests/test_cli.py
git commit -m "feat: collapse backend/frontend coders into one implementer agent (G5a)"
```

---

## Task 2: Stack-command detection in `detect.py` (G5b)

**Files:**
- Modify: `src/ade/detect.py`
- Test: `tests/test_detect.py`

**Interfaces:**
- Produces: `ProjectInfo.commands: dict[str, dict[str, str]]` — `{language: {"build", "lint", "format", "test"}}`. Each slot is a real command, the literal `none` (known language, slot not applicable), or `# set your <slot> command` (unknown/undetected language). Consumed by `stack.md.j2` in Task 3.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_detect.py`:

```python
def test_detect_commands_python(python_project: Path) -> None:
    info = detect_project(python_project)
    py = info.commands["python"]
    assert py["lint"] == "ruff check"
    assert py["format"] == "ruff format"
    assert py["test"] == "pytest --tb=short -q"
    # Python has no separate build step → not-applicable slot renders "none".
    assert py["build"] == "none"


def test_detect_commands_node(node_project: Path) -> None:
    info = detect_project(node_project)
    ts = info.commands["typescript"]
    assert ts["build"] == "npm run build"
    assert ts["lint"] == "npm run lint"
    # package.json scripts.test override flows through to the test slot.
    assert ts["test"] == "jest"


def test_detect_commands_unknown_language() -> None:
    from ade.detect import ProjectInfo, _detect_commands

    info = ProjectInfo(project_name="x", languages=["elixir"])
    _detect_commands(info.root, info)
    elixir = info.commands["elixir"]
    assert elixir["build"] == "# set your build command"
    assert elixir["test"] == "# set your test command"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_detect.py -v -k commands`
Expected: FAIL — `ProjectInfo` has no `commands` attribute / `_detect_commands` not defined.

- [ ] **Step 3: Add the `commands` field to `ProjectInfo`**

In `src/ade/detect.py`, in the `ProjectInfo` dataclass (after the `test_commands` field, around line 16), add:

```python
    commands: dict[str, dict[str, str]] = field(default_factory=dict)
```

- [ ] **Step 4: Add the per-language default command maps**

In `src/ade/detect.py`, immediately after `_DEFAULT_TEST_COMMANDS` (after line 62), add. Note: not-applicable slots are deliberately **omitted** (no `python` build key) so the three-state logic can render `none` for them.

```python
# Default build/lint/format commands per language. Slots that do not apply to a
# language are OMITTED here (e.g. python has no separate build) — the omission is what
# drives the "none" three-state rendering in _detect_commands.
_DEFAULT_BUILD_COMMANDS: dict[str, str] = {
    "javascript": "npm run build",
    "typescript": "npm run build",
    "go": "go build ./...",
    "rust": "cargo build",
}
_DEFAULT_LINT_COMMANDS: dict[str, str] = {
    "python": "ruff check",
    "javascript": "npm run lint",
    "typescript": "npm run lint",
    "go": "go vet ./...",
    "rust": "cargo clippy",
}
_DEFAULT_FORMAT_COMMANDS: dict[str, str] = {
    "python": "ruff format",
    "javascript": "npm run format",
    "typescript": "npm run format",
    "go": "gofmt -l .",
    "rust": "cargo fmt --check",
}

# Slot name → its per-language default map. Order defines the rendered order.
_SLOT_DEFAULTS: dict[str, dict[str, str]] = {
    "build": _DEFAULT_BUILD_COMMANDS,
    "lint": _DEFAULT_LINT_COMMANDS,
    "format": _DEFAULT_FORMAT_COMMANDS,
    "test": _DEFAULT_TEST_COMMANDS,
}

# A language is "known" if ADE ships defaults for it (keyed off the test map, which
# has an entry for every supported language).
_KNOWN_LANGUAGES: frozenset[str] = frozenset(_DEFAULT_TEST_COMMANDS)
```

- [ ] **Step 5: Add the `_detect_commands` step and call it**

In `src/ade/detect.py`, add the function (place it after `_detect_test_commands`, before `_detect_project_name`):

```python
def _detect_commands(root: Path, info: ProjectInfo) -> None:
    """Populate info.commands with a build/lint/format/test block per language.

    Three slot states keep the rendered file honest:
    - a present per-language default → the command;
    - an omitted slot for a *known* language → the literal ``none`` (phases skip it);
    - any slot for an *unknown/undetected* language → a ``# set your <slot> command``
      placeholder for the user to fill in.
    The test slot reuses the package.json override already captured in test_commands.
    """
    for lang in info.languages:
        known = lang in _KNOWN_LANGUAGES
        slots: dict[str, str] = {}
        for slot, defaults in _SLOT_DEFAULTS.items():
            if slot == "test" and lang in info.test_commands:
                slots[slot] = info.test_commands[lang]
            elif lang in defaults:
                slots[slot] = defaults[lang]
            elif known:
                slots[slot] = "none"
            else:
                slots[slot] = f"# set your {slot} command"
        info.commands[lang] = slots
```

Then in `detect_project` (after the `_detect_test_commands(root, info)` call, around line 77) add:

```python
    _detect_commands(root, info)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest tests/test_detect.py -v`
Expected: PASS (all detect tests, including the three new ones).

- [ ] **Step 7: Lint and commit**

```bash
ruff check src/ade/detect.py tests/test_detect.py
git add src/ade/detect.py tests/test_detect.py
git commit -m "feat: detect build/lint/format/test commands per language (G5b)"
```

---

## Task 3: Seed `.claude/ade-stack.md` (G5b)

**Files:**
- Create: `src/ade/templates/stack.md.j2`
- Modify: `src/ade/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `ProjectInfo.commands` from Task 2.
- Produces: `.claude/ade-stack.md` (seed-if-missing). Phase skills and `claude_md_section` reference it by path.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_init_seeds_ade_stack_file(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    stack = python_project / ".claude" / "ade-stack.md"
    assert stack.exists()
    content = stack.read_text()
    assert "build:" in content
    assert "lint:" in content
    assert "test:" in content
    # python block carries the detected commands
    assert "ruff check" in content


def test_init_ade_stack_seed_if_missing_preserves_edits(python_project: Path) -> None:
    stack = python_project / ".claude" / "ade-stack.md"
    stack.parent.mkdir(parents=True, exist_ok=True)
    stack.write_text("# my edited stack\n- test: make check\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited stack" in stack.read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cli.py -v -k ade_stack`
Expected: FAIL — `ade-stack.md` is not generated.

- [ ] **Step 3: Create the stack template**

Create `src/ade/templates/stack.md.j2` (the `{% if %}` fallback covers an empty/undetected project so the file is always valid and actionable):

```markdown
# ADE stack commands

ADE phase skills read this file for the project's commands. `ade init` seeds it from
stack detection; edit any line to correct it. One block per detected language. A value of
`none` means "not applicable — skip this step"; a `# set your <slot> command` line means
detection could not infer it — fill it in.

{% if info.commands %}
{% for lang, slots in info.commands.items() %}
## {{ lang }}
- build:  {{ slots.build }}
- lint:   {{ slots.lint }}
- format: {{ slots.format }}
- test:   {{ slots.test }}

{% endfor %}
{% else %}
## <language>
- build:  # set your build command
- lint:   # set your lint command
- format: # set your format command
- test:   # set your test command
{% endif %}
```

- [ ] **Step 4: Wire the seed into `cli.py`**

In `src/ade/cli.py`, inside `init`, after the hooks block and before "Update CLAUDE.md with ADE section" (i.e. after line 229's `else:` branch closes, before line 231), add:

```python
    # Seed .claude/ade-stack.md (G5b) — ADE-tooling config, seed-if-missing, user-owned.
    stack_dest = project_dir / ".claude" / "ade-stack.md"
    if _render_and_write_if_missing(env, "stack.md.j2", stack_dest, ctx):
        rprint("  [green]+[/green] Created .claude/ade-stack.md")
    else:
        rprint("  [dim]= Kept existing .claude/ade-stack.md[/dim]")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_cli.py -v -k ade_stack`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/stack.md.j2 src/ade/cli.py tests/test_cli.py
git commit -m "feat: seed .claude/ade-stack.md from detected commands (G5b)"
```

---

## Task 4: De-hardcode the detail phase skills 00/02/03/04/05 (G5b + acceptance-by-tests)

**Files:**
- Modify: `src/ade/templates/skills/phases/00-intent.md.j2`, `02-plan.md.j2`, `03-design-check.md.j2`, `04-implement.md.j2`, `05-quality-gate.md.j2`
- Test: `tests/test_cli.py` (existing `test_phase4_skill_describes_author_separation` must stay green)

**Interfaces:**
- Produces: phase skills with no `@vitals` / `packages/...` / `npm run ... -w` / `import type` / `shared → backend → frontend` references; commands referenced generically via `.claude/ade-stack.md`; `00-intent` introduces the `(manual)` acceptance tag; `04-implement` references the single `implementer` and maps each automatable criterion to a test.

- [ ] **Step 1: Rewrite `00-intent.md.j2`** — generalize Affected Areas and add the `(manual)` rule.

Replace the Output Format Acceptance Criteria + Affected Areas block (lines 28–36):

```markdown
## Acceptance Criteria
- [ ] Criterion 1 — specific, testable outcome
- [ ] Criterion 2 — specific, testable outcome
- [ ] Criterion 3 — specific, testable outcome

## Affected Areas
- packages/shared: <what changes>
- packages/backend: <what changes>
- packages/frontend: <what changes>
```
with:
```markdown
## Acceptance Criteria
- [ ] Criterion 1 — specific, automatable outcome
- [ ] Criterion 2 — specific, automatable outcome
- [ ] Criterion 3 (manual) — visual/perceptual, verified by a human outside the loop

## Affected Areas
- <area / module>: <what changes>
- <area / module>: <what changes>
```

Replace the `### Acceptance Criteria` field guideline (lines 54–59):

```markdown
### Acceptance Criteria
Each criterion must be independently verifiable. Use this test: could a reviewer look at
the running system and confirm yes/no whether this criterion is met?

Bad: "The UI looks good." (subjective)
Good: "The nutrition table renders rows for each day in the selected date range." (verifiable)
```
with:
```markdown
### Acceptance Criteria
Each criterion must be independently verifiable, and must be **expressible as an
automated test** to count as in-loop. Use this test: could a reviewer write a test that
confirms yes/no whether this criterion is met?

A criterion that is inherently visual or perceptual (e.g. "the toast appears", "the
layout looks right") cannot be captured by a test. Tag it `(manual)` — it is verified by
a human *outside* the ADE loop, not by the pipeline. The pipeline guarantees exactly what
the tests guarantee; it does not pretend a shallow render-test stands in for human review.

Bad: "The UI looks good." (subjective — tag `(manual)` if it must be kept)
Good: "The export endpoint returns CSV with one row per day in the range." (automatable)
```

Replace the `### Affected Areas` field guideline (lines 61–64):

```markdown
### Affected Areas
List every package that will have file changes. This drives the build order in later phases
and helps scope the research phase. If unsure, list as "possibly affected" and confirm
during research.
```
with:
```markdown
### Affected Areas
List every area or module that will have file changes. This helps scope the research
phase and informs the plan's dependency-ordered task list. If unsure, list as "possibly
affected" and confirm during research.
```

Also in the "Bad/Good" example near the workout page (lines 81–84) leave as-is (no stack hardcoding there).

- [ ] **Step 2: Rewrite `02-plan.md.j2`** — generalize the build-order rule, example task list, files table, and plan-gate checklist.

Replace line 36:
```markdown
**Build order rule:** shared types → backend → frontend. Always.
```
with:
```markdown
**Dependency-order rule:** build dependencies before dependents. The plan's ordered task
list / DAG defines the order — there is no fixed package order.
```

Replace the example task list (lines 38–56) with a stack-neutral example:
```markdown
```markdown
## 2. Task List

### Foundation (build first — shared contracts / types)
1. Add the `ExportFormat` contract in the shared/contracts module
2. Re-export it from the module's public surface

### Core
3. Add the `export` query/operation in the data layer
4. Add the export entrypoint (route / handler / command)
5. Add unit tests for the query/operation
6. Add tests for the entrypoint

### Edge (depends on Core)
7. Add the client-side `useExport` accessor
8. Wire the Export action into the relevant view
9. Add view-level tests
```
```

Replace the Files table (lines 73–88) with:
```markdown
```markdown
## 3. Files

| Action | Path | Description |
|--------|------|-------------|
| CREATE | `<shared>/contracts/export.<ext>` | ExportFormat contract |
| MODIFY | `<shared>/index.<ext>` | Re-export new contract |
| MODIFY | `<core>/data/export_query.<ext>` | Add export query |
| MODIFY | `<core>/entrypoints/export.<ext>` | Add export entrypoint |
| CREATE | `<core>/entrypoints/export_test.<ext>` | Entrypoint tests |
| MODIFY | `<edge>/views/Export.<ext>` | Add export action |
| CREATE | `<edge>/accessors/use_export.<ext>` | Export accessor |
| MODIFY | `docs/product-capabilities.md` | Add export capability |
| MODIFY | `docs/architecture.md` | Add export entrypoint to the surface table |
```
```

In Section 5 Test Strategy (lines 113–126), replace the nutrition-specific example with a neutral one:
```markdown
```markdown
## 5. Test Strategy

### Unit Tests
- `export_query` — verify output format, filtering, empty-result handling
- Export action component — render and trigger behavior

### Integration Tests
- None needed (no new external dependencies), or list them explicitly

### End-to-end / acceptance Tests
- Map each automatable Phase-0 acceptance criterion to at least one test here
```
```

Replace the Plan Gate checklist line 164:
```markdown
- [ ] Task list follows build order (shared → backend → frontend)
```
with:
```markdown
- [ ] Task list is dependency-ordered (dependencies before dependents)
```

- [ ] **Step 3: Rewrite `03-design-check.md.j2`** — replace the TypeScript stub snippets with language-neutral prose (spec §3.2 bullet 4).

Replace the entire "What Stubs Should Contain" section through the code blocks (lines 20–90) with:

```markdown
## What Stubs Should Contain

Stubs define the **shape** of the code, not the logic. Regardless of language, a stub is:

- **Type / data definitions** — written in full (the contract the rest of the code binds
  to): record/struct/interface shapes, enums, and the fields each carries.
- **Function / method signatures** — name, parameters with types, and return type, with a
  body that is a placeholder that fails loudly (raise/throw "not implemented", or the
  language's equivalent).
- **Entrypoint shells** — route/handler/command registration with the signature wired up
  but the body a placeholder.
- **Component / view shells** — the props/inputs contract plus an empty or null render.
- **Accessor / hook shells** — the signature and the returned shape, with placeholder
  values.

The placeholder marker must be one the `check-leftover-stub` hook recognizes so it can
never be shipped as real code (`Not implemented` / `NotImplementedError` /
`TODO: implement`).
```

Replace the "What Stubs Should NOT Contain" + "Validating Stubs Against Plan" build-check (lines 92–110). Specifically change the Validating list item 3 (lines 107–109):
```markdown
2. **Type consistency** — Types flow correctly across package boundaries
   (shared → backend, shared → frontend).
3. **Build check** — Run `npm run build -w @vitals/shared` to verify shared types compile.
   Other packages may not build yet (stubs throw), but there should be no type errors.
```
with:
```markdown
2. **Type consistency** — shared contracts/types flow correctly to every module that
   depends on them (dependencies before dependents).
3. **Build check** — run the project's `build` command (see `.claude/ade-stack.md`) for
   the foundation module to verify the shared contracts compile. Dependent modules may not
   build yet (stubs fail loudly), but there should be no contract/type errors. If `build`
   is `none` or unset for this stack, skip this check.
```

- [ ] **Step 4: Rewrite `04-implement.md.j2`** — implementer rename, criterion→test mapping, dependency order, drop the TS conventions.

Replace the 4b dispatch line (line 20):
```markdown
Dispatch the implementer subagent(s) (`backend-coder` / `frontend-coder`). They:
```
with:
```markdown
Dispatch the `implementer` subagent(s) — multiple instances with disjoint file
assignments when units are independent. They:
```

Add a sentence to the 4a section (after line 16, the test-only commit bullet) so the criterion→test mapping is explicit:
```markdown
- Maps **each automatable acceptance criterion** from Phase 0 to at least one test.
  Criteria tagged `(manual)` are skipped (no test) — a human verifies them outside the loop.
```

Replace the "Build Order Enforcement" section (lines 44–58) with:
```markdown
## Build / Dependency Order

Build dependencies before dependents — the plan's ordered task list / DAG defines the
order; there is no fixed package order. After completing each unit of work, run the
project's `build` command (see `.claude/ade-stack.md`) for the affected module before
moving on. If `build` is `none` or unset for this stack, rely on the `test` command
instead. Do not accumulate build errors across tasks.
```

Replace the shared-type conflict bullet (lines 66–68):
```markdown
- Shared type files (`packages/shared/src/types/`) are especially prone to conflicts —
  assign all shared type work to a single agent.
```
with:
```markdown
- Shared contract/type files are especially prone to conflicts — assign all shared-type
  work to a single agent.
```

Replace the "Convention Reference" key-conventions list (lines 88–93):
```markdown
Key conventions to enforce:
- 4-space indentation for Java, 2-space for everything else
- `import type` for type-only imports (enforced by ESLint)
- Explicit types over `var` in Java; `interface` over `type` for object shapes in TS
- Single quotes, semicolons, 100-char line width (Prettier)
- Unused variables prefixed with `_`
```
with:
```markdown
Key conventions come from the project, not from ADE:
- Indentation, quoting, and line width: follow CLAUDE.md and the existing files in the
  same directory.
- Lint/format rules are enforced by the project's `lint`/`format` commands
  (see `.claude/ade-stack.md`) — run them rather than hand-applying style rules.
- Match the naming, export, and error-handling style of neighboring code.
```

Replace the "Splitting Strategy" table (lines 72–78) — its "By package" rows assume the JS layout. Change to:
```markdown
| Pattern | When to use |
|---------|------------|
| **By module** | One agent per top-level module with clear boundaries (most common) |
| **By feature slice** | Each agent owns a vertical slice (contract + entrypoint + view) |
| **By layer** | One agent does all data queries, another all entrypoints |

The "by module" split is safest because modules have clear boundaries.
```

- [ ] **Step 5: Rewrite `05-quality-gate.md.j2`** — replace all `npm run ...` with stack-command references and drop the E2E/Prettier/`import type` specifics.

Replace the four check steps (lines 16–52) with:
```markdown
### Step 1: Lint
Run the project's `lint` command (see `.claude/ade-stack.md`). All lint errors must be
resolved. Warnings are acceptable only if pre-existing (not introduced by this task).

### Step 2: Format
Run the project's `format` command (see `.claude/ade-stack.md`); if it reports issues,
apply the fix and re-check.

### Step 3: Build
Run the project's `build` command (see `.claude/ade-stack.md`) for each changed module,
dependencies before dependents. Everything must build with zero errors.

### Step 4: Tests
Run the project's `test` command (see `.claude/ade-stack.md`). All tests must pass — zero
failures allowed for merge.

**If a command is `none` or unset for this stack, skip that step.** For a multi-language
repo, run the command block for each language whose files changed in this task.
```

Replace the `git stash` example (lines 63–66):
```markdown
```bash
git stash && npm run lint && git stash pop
```
```
with:
```markdown
```bash
git stash && <lint command from .claude/ade-stack.md> && git stash pop
```
```

Replace the "Common Fix Patterns" table rows that name TS/Prettier (lines 90 and 92):
```markdown
| `consistent-type-imports` | Change `import { X }` to `import type { X }` |
```
→ delete this row.
```markdown
| Prettier formatting | Run `npm run format` |
```
→
```markdown
| Formatting violation | Run the project's `format` command |
```

Replace the Pass Criteria checklist (lines 113–118):
```markdown
- [ ] `npm run lint` — zero errors
- [ ] `npm run format:check` — zero issues
- [ ] All packages build successfully
- [ ] `npm run test` — all tests pass
- [ ] `npm run test:e2e` — all E2E tests pass (if applicable)
```
with:
```markdown
- [ ] `lint` command — zero errors
- [ ] `format` command — zero issues
- [ ] `build` command — all changed modules build (skip if `none`)
- [ ] `test` command — all tests pass
```

- [ ] **Step 6: Run the affected test + verify no stack leaks in these five files**

Run: `pytest tests/test_cli.py::test_phase4_skill_describes_author_separation -v`
Expected: PASS (the assertions — `test-writer`, RED/failing, "separate"/"author separation" — survive the rewrite).

Run: `grep -rnE '@vitals|npm run|packages/(shared|backend|frontend)|import type|shared → backend' src/ade/templates/skills/phases/0[02345]-*.md.j2`
Expected: no output.

- [ ] **Step 7: Commit**

```bash
git add src/ade/templates/skills/phases/00-intent.md.j2 \
        src/ade/templates/skills/phases/02-plan.md.j2 \
        src/ade/templates/skills/phases/03-design-check.md.j2 \
        src/ade/templates/skills/phases/04-implement.md.j2 \
        src/ade/templates/skills/phases/05-quality-gate.md.j2
git commit -m "docs: de-hardcode stack from phase skills 00-05 (G5b)"
```

---

## Task 5: `06-review.md.j2` — acceptance-coverage gate + 4th lens (G5c acceptance-by-tests)

**Files:**
- Modify: `src/ade/templates/skills/phases/06-review.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `06-review.md` containing an acceptance-coverage gate, a 4th "Test adequacy" fallback lens, de-hardcoded `import type` text, and "Docs (Phase 7)" wording instead of "verify phase".

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_review_skill_has_acceptance_coverage_gate(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (
        python_project / ".claude" / "skills" / "ade" / "phases" / "06-review.md"
    ).read_text()
    assert "acceptance-coverage gate" in review.lower()
    assert "Test adequacy" in review
    # acceptance is now the in-loop check; verify-phase wording is gone
    assert "verify phase" not in review.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_review_skill_has_acceptance_coverage_gate -v`
Expected: FAIL.

- [ ] **Step 3: Add the 4th fallback lens**

In `06-review.md.j2`, after "### Lens 3: Security" and its bullet list (after line 75), add:

```markdown
### Lens 4: Test adequacy

Tests are now the sole in-loop proof of acceptance, so review them as rigorously as the
code. (The preferred mechanism's `pr-test-analyzer` already covers this — this lens closes
the gap in fallback mode.)

**What to look for:**
- **Tautologies** — assertions that can never fail (`assert True`, asserting a literal you
  just defined, re-asserting a mock's return value).
- **All-mocks / no real call** — the unit under test is fully mocked away, so the test
  exercises nothing real.
- **Missing edge cases** — empty inputs, error paths, boundaries from the spec untested.
- **Criterion coverage** — every automatable Phase-0 acceptance criterion has a test that
  *meaningfully exercises* it (not a shallow render or a tautology).
```

- [ ] **Step 4: Add the acceptance-coverage gate**

In `06-review.md.j2`, immediately before "## Severity Classification" (before line 77), add:

```markdown
## Acceptance-Coverage Gate

Because live verification has been removed from the pipeline, this gate is the in-loop
acceptance check — it replaces live evidence:

- **Every automatable Phase-0 acceptance criterion must have a covering test that
  meaningfully exercises it** (not a tautology, not all-mocks). A criterion with no test,
  or only an empty/tautological one, is an **Important** finding that must be resolved.
- **`(manual)` criteria** are not blockers — list them in the review summary as
  human-verify items for the reviewer to check outside the loop.

```

- [ ] **Step 5: De-hardcode the conventions lens and fix verify-phase wording**

Replace line 53:
```markdown
- Import style — `import type` for type-only imports, consistent ordering
```
with:
```markdown
- Import style — follows the project's import conventions and ordering
```

Replace line 113:
```markdown
1. **Critical findings** — Fix immediately. Do not proceed to verify phase.
```
with:
```markdown
1. **Critical findings** — Fix immediately. Do not proceed to Docs (Phase 7).
```

Replace line 132 (inside "On review pass"):
```markdown
3. Proceed to Phase 7
```
with:
```markdown
3. Proceed to Docs (Phase 7)
```

(The example findings table at lines 142–148 mentions `import type` / `interface`; replace the line `| 3 | types/export.ts | 5 | Uses \`type\` instead of \`interface\` | Change to interface |` with `| 3 | export module | 5 | Type fails to express an invariant | Tighten the type |` to avoid a TS-specific example.)

- [ ] **Step 6: Run the test + commit**

Run: `pytest tests/test_cli.py::test_review_skill_has_acceptance_coverage_gate -v`
Expected: PASS.

```bash
git add src/ade/templates/skills/phases/06-review.md.j2 tests/test_cli.py
git commit -m "docs: add acceptance-coverage gate + test-adequacy lens to review (G5c)"
```

---

## Task 6: Remove live verification + renumber the tail (G5c)

**Files:**
- Delete: `src/ade/templates/skills/phases/07-verify.md.j2`, `src/ade/templates/skills/phases/qa-verify-bug.md.j2`
- Rename: `08-docs.md.j2`→`07-docs.md.j2`, `09-ship.md.j2`→`08-ship.md.j2`, `10-retro.md.j2`→`09-retro.md.j2`
- Modify (content of the renamed files): `07-docs.md.j2`, `08-ship.md.j2`, `09-retro.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: a clean `00–09` phase sequence under `.claude/skills/ade/phases/`; no `07-verify.md` / `qa-verify-bug.md`; `09-retro.md` with no verify metrics; `08-ship.md` with no screenshot/visual-verification section.

- [ ] **Step 1: Update the phase-doc tests (write failing tests first)**

Replace `test_init_generates_phase_docs` (lines 150–157):
```python
def test_init_generates_phase_docs(python_project: Path) -> None:
    """Phase reference docs should be generated, renumbered 0–9 with no verify phase."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    phases_dir = python_project / ".claude" / "skills" / "ade" / "phases"
    assert phases_dir.is_dir()
    assert (phases_dir / "00-intent.md").exists()
    assert (phases_dir / "07-docs.md").exists()
    assert (phases_dir / "08-ship.md").exists()
    assert (phases_dir / "09-retro.md").exists()
    # live verification is gone
    assert not (phases_dir / "07-verify.md").exists()
    assert not (phases_dir / "qa-verify-bug.md").exists()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_cli.py::test_init_generates_phase_docs -v`
Expected: FAIL — `07-docs.md` doesn't exist yet; `07-verify.md` still rendered.

- [ ] **Step 3: Delete the two live-verify phase files**

```bash
git rm src/ade/templates/skills/phases/07-verify.md.j2 \
       src/ade/templates/skills/phases/qa-verify-bug.md.j2
```

- [ ] **Step 4: Rename the tail files (highest number first)**

```bash
git mv src/ade/templates/skills/phases/10-retro.md.j2 src/ade/templates/skills/phases/09-retro.md.j2
git mv src/ade/templates/skills/phases/09-ship.md.j2  src/ade/templates/skills/phases/08-ship.md.j2
git mv src/ade/templates/skills/phases/08-docs.md.j2  src/ade/templates/skills/phases/07-docs.md.j2
```

- [ ] **Step 5: Renumber `07-docs.md.j2` (was 08) content**

Replace line 1 `# Phase 8 — Documentation` → `# Phase 7 — Documentation`.
Replace line 137 `Before proceeding to Phase 9:` → `Before proceeding to Ship (Phase 8):`.
Replace the E2E-coverage example (line 48 `**E2E Coverage:** \`e2e/nutrition-export.spec.ts\``) → `**Test Coverage:** the acceptance tests covering this capability`.
Replace the checklist line 144 `- [ ] E2E coverage references point to actual test files` → `- [ ] Test-coverage references point to actual test files`.

- [ ] **Step 6: Renumber + de-hardcode `08-ship.md.j2` (was 09) content — drop screenshots, add test/acceptance summary**

Replace line 1 `# Phase 9 — Commit & PR` → `# Phase 8 — Commit & PR`.

Replace the staging example (lines 73–77):
```markdown
git add packages/shared/src/types/export.ts
git add packages/backend/src/routes/nutrition.ts
git add packages/backend/src/db/queries/measurements.ts
# ... etc
```
with:
```markdown
git add <changed source files for this task>
# Stage only files that belong to this change.
```

Replace the PR Body Template (lines 108–133) with a screenshot-free body that carries a test/acceptance summary:
```markdown
```markdown
## Summary
- <1–3 bullets describing the change>

## Acceptance Coverage
- Each automatable Phase-0 criterion → the (green) test(s) that cover it
- Any `(manual)` criteria, listed for the human reviewer to verify

## Test Results
- <test command from .claude/ade-stack.md> — all green

## Changes
- <path> — <what changed>
```
```

Replace the "Visual Verification" / screenshot upload sections. Delete the `### Uploading Screenshots to PR` block and the bugfix before/after block (lines 154–176) entirely. In the `gh pr create` example (lines 137–152) keep it but ensure the body has no screenshot reference (already fine). In the Merge Gate "Provide" list (lines 183–187), replace `- Test results` is fine; leave it. Remove no other.

Also remove the PR-body `## Visual Verification` lines that were inside the template body above (covered by the PR Body Template replacement).

- [ ] **Step 7: Renumber + strip verify metrics from `09-retro.md.j2` (was 10)**

Replace line 1 `# Phase 10 — Retrospective` → `# Phase 9 — Retrospective`.

In the `cycleTime.phases` JSON example (lines 20–32), remove the `"verify": "10m",` line.

In the `iterations` JSON example (lines 35–41), remove the `"verifyRejectCycles": 0,` line.

In "### iterations" explanation (lines 89–94), remove the bullet `- **verifyRejectCycles** — how many verify-fail-fix loops (max 2)`.

In the "Task Directory Structure (Final)" tree (lines 146–157), remove the `verification/` block so it reads:
```markdown
```
.ade/tasks/<task-id>/
├── intent.md
├── plan.md
├── status.json
└── retro.json
```
```

- [ ] **Step 8: Run the phase-doc test + the suite**

Run: `pytest tests/test_cli.py::test_init_generates_phase_docs -v`
Expected: PASS.

Run: `pytest -q`
Expected: only the *known* still-pending failures remain — `test_init_skills_have_phase_content` (Phase 10 still in `ade-full`, fixed in Task 7) still passes because `ade-full` retains "RETROSPECTIVE"; `test_init_full_skill_has_live_verification` still passes (ade-full not yet rewritten). If anything else fails, stop and fix before committing.

- [ ] **Step 9: Commit**

```bash
git add -A src/ade/templates/skills/phases tests/test_cli.py
git commit -m "feat: remove live-verify phases and renumber tail to 0-9 (G5c)"
```

---

## Task 7: Rewrite `ade-full.md.j2` (G5c — the pipeline spine)

**Files:**
- Modify: `src/ade/templates/skills/ade-full.md.j2`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: a 9-phase `ade-full.md` (0–9) with no Phase 7 verify, no QA-verify block, no `docker`/`Playwright`/`localhost`, no `/10` status strings, the single `implementer`, dependency-order language, and the `Verify→review reject` circuit breaker dropped.

- [ ] **Step 1: Update the ade-full tests (write failing tests first)**

Replace `test_init_skills_have_phase_content` (lines 81–91):
```python
def test_init_skills_have_phase_content(python_project: Path) -> None:
    """Skills should contain phase instructions, renumbered 0–9."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    full = (python_project / ".claude" / "skills" / "ade" / "ade-full.md").read_text()
    assert "Phase 0" in full
    assert "Phase 9" in full or "RETROSPECTIVE" in full
    assert "Circuit Breaker" in full or "circuit breaker" in full.lower()

    plan = (python_project / ".claude" / "skills" / "ade" / "ade-plan.md").read_text()
    assert "PLAN" in plan or "plan" in plan
```

Delete `test_init_full_skill_has_live_verification` (lines 175–179) entirely.

Add a replacement guard:
```python
def test_init_no_live_verification(python_project: Path) -> None:
    """No live-verification machinery remains anywhere in the full pipeline skill."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    skills = python_project / ".claude" / "skills" / "ade"
    full = (skills / "ade-full.md").read_text()
    for token in ("Playwright", "docker compose", "localhost", "NO EXEMPTIONS", "/10"):
        assert token not in full, f"stale live-verify token in ade-full.md: {token}"
    phases = skills / "phases"
    assert not (phases / "07-verify.md").exists()
    assert not (phases / "qa-verify-bug.md").exists()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_cli.py -v -k "no_live_verification or phase_content"`
Expected: FAIL (ade-full still has `/10`, Phase 7 verify, etc.).

- [ ] **Step 3: Rewrite `ade-full.md.j2` to the final 9-phase content**

Apply these edits to `src/ade/templates/skills/ade-full.md.j2`:

1. Line 16 (`Non-degradable quality gates`): replace
```markdown
Non-degradable quality gates: live verification with evidence, build/lint/test validation, documentation updates.
```
with
```markdown
Non-degradable quality gates: acceptance-coverage by tests, build/lint/test validation, documentation updates.
```

2. Pipeline Overview block (lines 20–26): replace with
```markdown
```
Phase 0: Intent → Phase 1: Research → ◆ USER GATE
   → Phase 2: Plan → ◆ PLAN GATE → Phase 3: Design Check
   → Phase 4: Implement → Phase 5: Quality Gate → Phase 6: Review
   → Phase 7: Docs → Phase 8: Ship → ◆ MERGE GATE → Phase 9: Retro
```
```

3. Delete the entire `## QA VERIFY (bugs only …)` section (lines 57–69), including its surrounding `---` separators so Phase 0 flows directly into Phase 1.

4. All status strings `Phase N/10` → `Phase N/9`: line 45 `Phase 0/10`→`Phase 0/9`; line 129 `Phase 2/10`→`Phase 2/9`; line 155 `Phase 3/10`→`Phase 3/9`; line 184 `Phase 4/10`→`Phase 4/9`; line 209 `Phase 5/10`→`Phase 5/9`; line 254 `Phase 6/10`→`Phase 6/9`.

5. Phase 2 required section 2 (line 123): replace `2. **Ordered task list** — dependency-aware (shared types → backend → frontend)` with `2. **Ordered task list** — dependency-aware (dependencies before dependents; the task DAG defines order)`.

6. Phase 2 test-strategy line 126: replace `5. **Test strategy** — unit tests, integration tests, E2E tests` with `5. **Test strategy** — unit, integration, and acceptance tests; map each automatable Phase-0 criterion to a test`.

7. Phase 4b (lines 172–176): replace
```markdown
**Step 4b — implementer (GREEN):** Dispatch `backend-coder` / `frontend-coder` subagents.
They receive the spec, the committed failing tests, and the stubs — but NOT the
test-writer's reasoning (structural generator≠verifier separation). They write the
minimum code to turn the suite GREEN, leaving no stub markers in committed source.
Enforce build order: shared types → backend → frontend.
```
with
```markdown
**Step 4b — implementer (GREEN):** Dispatch one or more `implementer` subagents with
disjoint file assignments. They receive the spec, the committed failing tests, and the
stubs — but NOT the test-writer's reasoning (structural generator≠verifier separation).
They write the minimum code to turn the suite GREEN, leaving no stub markers in committed
source. Build dependencies before dependents — the plan's task DAG defines the order.
```

8. Phase 5 steps (lines 200–206): replace
```markdown
1. Run lint — must pass with 0 errors in changed files
2. Run format check — changed files must pass
3. Run build — must compile
4. Run unit tests — all must pass
5. Run E2E tests — all must pass
```
with
```markdown
1. Run the `lint` command — 0 errors in changed files
2. Run the `format` command — changed files must pass
3. Run the `build` command — must compile (skip if `none`)
4. Run the `test` command — all tests pass

Commands come from `.claude/ade-stack.md`; skip any slot that is `none` or unset. For a
multi-language change, run each affected language's block.
```

9. Phase 6 "On Review Pass" line 252: `3. Proceed to Phase 7` → `3. Proceed to Docs (Phase 7)`.

10. Delete the entire `## Phase 7 — VERIFY` section (lines 262–287) including one bounding `---`.

11. Renumber the remaining phase headings/links/status lines:
    - `## Phase 8 — DOCUMENTATION` → `## Phase 7 — DOCUMENTATION`; its link `[phases/08-docs.md]` → `[phases/07-docs.md]`; its status `Phase 8/10 — Docs updated` → `Phase 7/9 — Docs updated`.
    - `## Phase 9 — SHIP` → `## Phase 8 — SHIP`; link `[phases/09-ship.md]` → `[phases/08-ship.md]`; status `Phase 9/10 — PR created` → `Phase 8/9 — PR created`. Remove ship step 5 (`5. For UI changes: upload verification screenshots as PR comment`) and step 6 (`6. For bugfixes: include before/after evidence section`); replace them with `5. Include the acceptance-coverage + test-results summary in the PR body`.
    - `## Phase 10 — RETROSPECTIVE` → `## Phase 9 — RETROSPECTIVE`; status `Phase 10/10 — Complete` → `Phase 9/9 — Complete`. In the retro bullet list, change `Iteration counts (design check, code-review, QA fix, verify-reject)` → `Iteration counts (design check, code-review, QA fix)`.

12. Circuit Breakers list (lines 362–368): delete the `- Verify→review reject: max 2 cycles` line.

13. Update the human-gate references in any retained prose (the MERGE GATE section already sits after Ship; no further change needed). Verify no remaining `Phase 10` / `/10` / `docker` / `Playwright` / `localhost` text by the grep in Step 4.

- [ ] **Step 4: Verify no stale tokens + run tests**

Run: `grep -nE 'docker|Playwright|localhost|/10|Phase 10|backend-coder|frontend-coder|@vitals' src/ade/templates/skills/ade-full.md.j2`
Expected: no output.

Run: `pytest tests/test_cli.py -v -k "no_live_verification or phase_content or exit_criteria"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/skills/ade-full.md.j2 tests/test_cli.py
git commit -m "feat: rewrite ade-full as 9-phase stack-neutral pipeline (G5c)"
```

---

## Task 8: Composite skills `ade-code`, `ade-review`, `ade-ship` + the `ade_review` command wrapper

**Files:**
- Modify: `src/ade/templates/skills/ade-code.md.j2`, `src/ade/templates/skills/ade-review.md.j2`, `src/ade/templates/skills/ade-ship.md.j2`, `src/ade/templates/commands/ade_review.md.j2`

**Interfaces:**
- Produces: composite skills referencing the single `implementer`, dependency order, no live verify, renumbered phases (Ship = 8, Retro = 9), and stack-command references. `ade-review` is retitled "Review + Documentation".

- [ ] **Step 1: Rewrite `ade-code.md.j2`**

Replace lines 10–21:
```markdown
## Phase 4 — IMPLEMENT (author-separated TDD)
Step 4a: dispatch `test-writer` → writes FAILING tests, commits them alone (`test:`).
Step 4b: dispatch implementer subagents (`backend-coder`/`frontend-coder`) → make tests
GREEN, commit alone (`feat:`/`fix:`). Enforce build order: shared → backend → frontend.
The orchestrator does NOT pass the test-writer's reasoning to the implementer.

**Hard requirement:** Tests start RED, end GREEN. No stub markers remain in source.
**Mechanism:** `block-mixed-commit` hook keeps test and impl commits separate.
**Exit criteria:** All tests pass. Build passes.

## Phase 5 — QUALITY GATE
Run: lint → format → build → unit tests → E2E tests.
```
with:
```markdown
## Phase 4 — IMPLEMENT (author-separated TDD)
Step 4a: dispatch `test-writer` → writes FAILING tests (one per automatable Phase-0
criterion), commits them alone (`test:`).
Step 4b: dispatch one or more `implementer` subagents with disjoint file assignments →
make tests GREEN, commit alone (`feat:`/`fix:`). Build dependencies before dependents
(the plan's task DAG defines order). The orchestrator does NOT pass the test-writer's
reasoning to the implementer.

**Hard requirement:** Tests start RED, end GREEN. No stub markers remain in source.
**Mechanism:** `block-mixed-commit` hook keeps test and impl commits separate.
**Exit criteria:** All tests pass. Build passes.

## Phase 5 — QUALITY GATE
Run the project's lint → format → build → test commands (see `.claude/ade-stack.md`);
skip any slot that is `none` or unset.
```

- [ ] **Step 2: Rewrite `ade-review.md.j2`** — drop Phase 7 Verify, retitle.

Replace line 1:
```markdown
Run ADE review phases (Review + Verify + Documentation) for: $ARGUMENTS
```
with:
```markdown
Run ADE review phases (Review + Documentation) for: $ARGUMENTS
```

Delete the entire `## Phase 7 — VERIFY (MANDATORY — NO EXEMPTIONS)` section (lines 29–41).

In the Phase 6 block, append after line 13 (the Security fallback bullet) a line:
```markdown
4. Test adequacy: tautologies, all-mocks, missing edge cases, each automatable criterion meaningfully exercised
```
And after the Phase 6 exit-criteria line 27, add an acceptance-gate line:
```markdown
**Acceptance gate:** every automatable Phase-0 criterion has a covering test that
meaningfully exercises it (missing/empty → Important). `(manual)` criteria are listed for
the human, not blockers.
```

Change the remaining `## Phase 8 — DOCUMENTATION` (line 43) → `## Phase 7 — DOCUMENTATION`.

- [ ] **Step 3: Rewrite `ade-ship.md.j2`** — renumber, drop screenshots.

Replace line 3 `## Phase 9 — SHIP` → `## Phase 8 — SHIP`.
Replace PR-body bullets (lines 8–13):
```markdown
4. Open PR with:
   - Summary (1-3 bullets)
   - Use Cases (UC IDs)
   - Test Plan (checklist)
   - Visual Verification (screenshots for UI changes)
   - Before/After Evidence (bugfixes only)
5. Upload verification screenshots as PR comment via `gh pr comment`
```
with:
```markdown
4. Open PR with:
   - Summary (1-3 bullets)
   - Use Cases (UC IDs)
   - Acceptance Coverage (each automatable criterion → its green test; `(manual)` items listed)
   - Test Results (the `test` command output summary)
```
Replace line 21 `## Phase 10 — RETROSPECTIVE` → `## Phase 9 — RETROSPECTIVE`.
Replace line 24 `- Iteration counts (design check, review, QA fix, verify reject)` → `- Iteration counts (design check, review, QA fix)`.

- [ ] **Step 4: Fix the `ade_review` command wrapper**

In `src/ade/templates/commands/ade_review.md.j2`, replace line 1:
```markdown
Run ADE review phases (Review + Verify + Documentation) for: $ARGUMENTS
```
with:
```markdown
Run ADE review phases (Review + Documentation) for: $ARGUMENTS
```

- [ ] **Step 5: Verify no stale tokens + run the suite**

Run: `grep -rnE 'backend-coder|frontend-coder|Phase 10|NO EXEMPTIONS|Playwright|/10' src/ade/templates/skills/ade-code.md.j2 src/ade/templates/skills/ade-review.md.j2 src/ade/templates/skills/ade-ship.md.j2 src/ade/templates/commands/ade_review.md.j2`
Expected: no output.

Run: `pytest -q`
Expected: PASS (full suite — `ade-pr-review` still has coder refs, but no test asserts on it yet; the Task 12 grep guard is not added until later).

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/skills/ade-code.md.j2 \
        src/ade/templates/skills/ade-review.md.j2 \
        src/ade/templates/skills/ade-ship.md.j2 \
        src/ade/templates/commands/ade_review.md.j2
git commit -m "docs: de-hardcode + renumber composite review/code/ship skills (G5c)"
```

---

## Task 9: `ade-pr-review.md.j2` (spec-gap fix — must pass the grep guard)

> The spec's §4 file list omits `ade-pr-review.md.j2`, but its §5 grep guard forbids any
> `backend-coder`/`frontend-coder` in the generated tree, and this skill dispatches both
> and references "Phase 9 MERGE GATE". This task closes that gap.

**Files:**
- Modify: `src/ade/templates/skills/ade-pr-review.md.j2`

**Interfaces:**
- Produces: PR-review skill that dispatches the single `implementer` and references the renumbered Ship gate (Phase 8).

- [ ] **Step 1: Replace coder dispatch in the intro (lines 3–6)**

```markdown
The orchestrator never edits code itself. It dispatches the `pr-reviewer` agent
to inspect the PR, then dispatches `backend-coder` / `frontend-coder` agents to
apply fixes inside the PR's worktree, then re-reviews until clean or the
iteration cap is hit.
```
→
```markdown
The orchestrator never edits code itself. It dispatches the `pr-reviewer` agent
to inspect the PR, then dispatches one or more `implementer` agents (disjoint file
assignments) to apply fixes inside the PR's worktree, then re-reviews until clean or the
iteration cap is hit.
```

- [ ] **Step 2: Replace the per-file dispatch rule (lines 36–38)**

```markdown
2. Group `actionable` findings by file. For each group, dispatch one coder
   subagent (`backend-coder` for server/lib code, `frontend-coder` for UI).
   Each agent owns its files — no overlap.
```
→
```markdown
2. Group `actionable` findings by file. For each group, dispatch one `implementer`
   subagent. Each agent owns its files — no overlap.
```

- [ ] **Step 3: Fix the renumbered merge-gate reference (line 67)**

```markdown
- Never auto-merge. The MERGE GATE in Phase 9 still applies.
```
→
```markdown
- Never auto-merge. The MERGE GATE after Ship (Phase 8) still applies.
```

- [ ] **Step 4: Verify + run the suite**

Run: `grep -nE 'backend-coder|frontend-coder|Phase 9' src/ade/templates/skills/ade-pr-review.md.j2`
Expected: no output.

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ade/templates/skills/ade-pr-review.md.j2
git commit -m "docs: de-hardcode coders to implementer in ade-pr-review (G5)"
```

---

## Task 10: `claude_md_section.md.j2` — de-hardcode, renumber, stack pointer (G5)

**Files:**
- Modify: `src/ade/templates/claude_md_section.md.j2`

**Interfaces:**
- Produces: the always-loaded CLAUDE.md ADE section with the single implementer, dependency order, a `Stack commands: see .claude/ade-stack.md` pointer, renumbered phases 7–9, and the `Verify→review reject` circuit breaker dropped.

- [ ] **Step 1: Replace Phase 4 description (lines 60–63)**

```markdown
**Phase 4 — IMPLEMENT**: test-writer (RED) → implementer (GREEN), author-separated.
Step 4a: `test-writer` subagent writes FAILING tests, commits them alone (`test:`).
Step 4b: `backend-coder`/`frontend-coder` make tests GREEN, commit alone (`feat:`/`fix:`).
Enforce build order: shared types → backend → frontend.
```
→
```markdown
**Phase 4 — IMPLEMENT**: test-writer (RED) → implementer (GREEN), author-separated.
Step 4a: `test-writer` subagent writes FAILING tests, commits them alone (`test:`).
Step 4b: one or more `implementer` subagents (disjoint file assignments) make tests GREEN,
commit alone (`feat:`/`fix:`). Build dependencies before dependents (the plan's task DAG
defines order).
```

- [ ] **Step 2: Add the stack-commands pointer**

After the Phase 4 block (after the lines edited in Step 1), insert:
```markdown

**Stack commands:** build/lint/format/test commands live in `.claude/ade-stack.md`
(seeded by `ade init`, user-owned). Phases reference it instead of hardcoding commands.
```

- [ ] **Step 3: Renumber Phases 7–10 (lines 74–91)**

Replace the block:
```markdown
**Phase 7 — VERIFY**: Run full test suite. Capture evidence for each
acceptance criterion from Phase 0.

**Phase 8 — DOCUMENTATION**: Update docs triggered by code changes:
```
with:
```markdown
**Phase 7 — DOCUMENTATION**: Update docs triggered by code changes:
```
(The Phase 7 — VERIFY paragraph is deleted; acceptance is proven by tests in Phases 4–6.)

Then:
- `**Phase 9 — COMMIT & PR**` (line 86) → `**Phase 8 — COMMIT & PR**`
- `**Phase 10 — RETROSPECTIVE**` (line 90) → `**Phase 9 — RETROSPECTIVE**`

- [ ] **Step 4: Drop the verify circuit breaker (lines 101–107)**

Delete the line `- Verify→review reject: max 2 cycles` from the Circuit Breaker list.

- [ ] **Step 5: Verify + run the suite**

Run: `grep -nE 'backend-coder|frontend-coder|Phase 10|Verify→review|shared types → backend' src/ade/templates/claude_md_section.md.j2`
Expected: no output.

Run: `pytest -q`
Expected: PASS (including `test_init_creates_claude_md_with_ade_section`).

- [ ] **Step 6: Commit**

```bash
git add src/ade/templates/claude_md_section.md.j2
git commit -m "docs: de-hardcode + renumber CLAUDE.md ADE section, add stack pointer (G5)"
```

---

## Task 11: Update the architecture doc (G5 §3.5)

**Files:**
- Modify: `docs/ade-architecture-design.md`

**Interfaces:**
- Produces: a 9-phase (0–9) architecture doc with a single `implementer` row, a stack-configuration subsection, and no verify row anywhere.

- [ ] **Step 1: Intro line (line 3)** — `10-phase SDLC` → `9-phase SDLC`.

- [ ] **Step 2: SDLC table (lines 34–48)** — change heading `## The 10-phase SDLC` → `## The 9-phase SDLC`; in the Phase 4 row replace `1–3 implementer subagents (GREEN)` actor wording to `test-writer (RED) → implementer (GREEN)`; delete the `| 7 — Verify | … |` row; renumber `8 — Docs`→`7 — Docs`, `9 — Ship`→`8 — Ship`, `10 — Retro`→`9 — Retro`.

- [ ] **Step 3: Human-gates line (line 50)** — `after Phase 9 (merge decision)` → `after Phase 8 (merge decision)`.

- [ ] **Step 4: "Phases 2–10" section (lines 199–211)** — heading `## Phases 2–10 (current state)` → `## Phases 2–9 (current state)`; in the Phase 4 bullet replace `1–3 implementer subagents (\`backend-coder\`, \`frontend-coder\`) drive those tests to GREEN … Build order: shared → backend → frontend.` with `one or more \`implementer\` subagents (disjoint file assignments) drive those tests to GREEN, never editing test files. Build dependencies before dependents (the task DAG defines order).`; delete the `- **Phase 7 — Verify**: …` bullet; renumber the Docs/Ship/Retro bullets to 7/8/9.

- [ ] **Step 5: Add a stack-configuration subsection.** After the renumbered "Phases 2–9" section (before "## Deterministic hook layer (G2)"), add:

```markdown
## Stack configuration (`.claude/ade-stack.md`)

`ade init` detects each language's build/lint/format/test commands and seeds them into
`.claude/ade-stack.md` (seed-if-missing, user-owned thereafter). Phase skills reference
this file generically rather than hardcoding commands, which is what makes the pipeline
stack-neutral. Three slot states keep it honest: a real command; `none` for a
known-language slot that does not apply (e.g. python has no build), which phases skip; and
`# set your <slot> command` for an unknown/undetected stack, which the user fills in. The
orchestrator reads the file and injects the concrete command into each subagent's dispatch
prompt; for a multi-language change it runs the block for each changed language.
```

- [ ] **Step 6: Subagent catalog (lines 246–247)** — replace the two rows
```markdown
| `backend-coder` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
| `frontend-coder` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
```
with one row:
```markdown
| `implementer` | sonnet | Read, Write, Edit, Bash, Glob, Grep | Phase 4b |
```

- [ ] **Step 7: Artifact contracts table (lines 264, 269–270)** — `docs/specs/...` consumed-by `Phase 2, Phase 7` → `Phase 2`; delete the `.ade/tasks/<id>/verification/` row; the retro row `Phase 10` → `Phase 9`; the `plan.md` row consumed-by `Phases 3–7` → `Phases 3–8`.

- [ ] **Step 8: Circuit-breaker table (lines 318–328)** — delete the `| Phase 7 verify → review reject | 2 cycles | Escalate to user |` row; relabel `Phase 4–6 code → review loop` stays; relabel `Phase 4 commit hooks` stays. No renumber needed beyond removing the verify row.

- [ ] **Step 9: Sweep for any remaining stale references**

Run: `grep -nE 'backend-coder|frontend-coder|10-phase|Phase 10|verify → review|Phase 7 — Verify' docs/ade-architecture-design.md`
Expected: no output (note: other legitimate "verify" mentions in the Research/R5 sections — Chain-of-Verification — are unrelated and stay).

- [ ] **Step 10: Commit**

```bash
git add docs/ade-architecture-design.md
git commit -m "docs: update architecture doc to 9-phase single-implementer model (G5)"
```

---

## Task 12: Final stale-reference grep guard + full suite green

**Files:**
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: the fully-rendered `.claude/` tree from a real `init`. Asserts none of the forbidden tokens survive anywhere.

- [ ] **Step 1: Write the guard test**

Add to `tests/test_cli.py`:

```python
def test_no_stale_stack_references(python_project: Path) -> None:
    """No pre-G5 stack/verify token may survive in the generated tree (spec §5)."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    claude_dir = python_project / ".claude"
    docs = [
        p
        for p in claude_dir.rglob("*.md")
        if "vendored" not in p.parts  # vendored skills keep their own wording
    ]
    docs.append(python_project / "CLAUDE.md")  # generated ADE section lives here
    blob = "\n".join(p.read_text() for p in docs if p.exists())
    forbidden = [
        "@vitals",
        "-w @",
        "backend-coder",
        "frontend-coder",
        "Playwright",
        "docker compose",
        "localhost",
        "NO EXEMPTIONS",
        "07-verify",
        "qa-verify",
        "/10",
    ]
    found = [tok for tok in forbidden if tok in blob]
    assert not found, f"stale references still present: {found}"
```

- [ ] **Step 2: Run the guard**

Run: `pytest tests/test_cli.py::test_no_stale_stack_references -v`
Expected: PASS. If it fails, the printed token list points at the file/concept missed in Tasks 4–11 — fix that template, do not weaken the test.

- [ ] **Step 3: Run the whole suite + lint**

Run: `pytest -q`
Expected: PASS — all tests green.

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: clean. If `ruff format --check` reports changes, run `ruff format src/ tests/` and re-run the suite.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: guard generated tree against stale pre-G5 stack references (G5)"
```

- [ ] **Step 5: Mark the spec implemented**

In `docs/superpowers/specs/2026-06-19-g5-implementer-stack-dehardcode-design.md`, change the status line 4 from `**Status:** Approved (design); pending implementation plan` to `**Status:** Implemented`. Commit:

```bash
git add docs/superpowers/specs/2026-06-19-g5-implementer-stack-dehardcode-design.md
git commit -m "docs: mark G5 spec implemented"
```

---

## Self-Review

**Spec coverage** (spec section → task):
- §3.1 G5a single implementer → Task 1. ✅
- §3.2 detect.py command maps + three-state + `commands` field → Task 2; `stack.md.j2` + cli seed + claude_md pointer → Tasks 3 & 10; multi-language selection rule stated in phases → Tasks 4/7. ✅
- §3.3 de-hardcode phase skills (02/03/04/05/ade-full/ade-code) → Tasks 4, 7, 8. ✅
- §3.4 remove live verify + renumber; acceptance-by-tests in 00/04/06; ship ripple; composite ripple; circuit breakers → Tasks 5, 6, 7, 8. ✅
- §3.5 architecture doc → Task 11. ✅
- §5 tests (update/add/remove + grep guard) → distributed across Tasks 1–12; guard in Task 12. ✅
- §6 edge cases (multi-language, unknown stack `# set your`, known not-applicable `none`, seed-if-missing) → Tasks 2 (`test_detect_commands_unknown_language`), 3 (`test_init_ade_stack_seed_if_missing_preserves_edits`). ✅
- Spec gaps covered beyond §4: `ade-pr-review.md.j2` (Task 9) and `commands/ade_review.md.j2` wrapper (Task 8) — both required by the §5 grep guard.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N" — every step gives the exact old→new text or full file content.

**Type/name consistency:** agent name `implementer` is used identically in Tasks 1, 7, 8, 9, 10, 11. `ProjectInfo.commands` defined in Task 2, consumed by `stack.md.j2` in Task 3. Phase numbering: Verify removed; Docs=7, Ship=8, Retro=9 used consistently in Tasks 6, 7, 8, 10, 11. Forbidden-token list is identical in the Global Constraints and the Task 12 guard.

**Known intentional non-changes:** `tests/test_cli.py::test_status_with_tasks` writes the literal status string `"Phase 4/10"` as *input* to the `status` command (not generated output), so it is not asserted against the generated tree and the Task 12 guard does not scan test files — left as-is to avoid scope creep.
