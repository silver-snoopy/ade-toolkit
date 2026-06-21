import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ade.cli import app

runner = CliRunner()


def test_init_python_project(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    # Verify v4 generated files
    assert (python_project / ".ade" / ".gitignore").exists()
    assert (python_project / ".claude" / "agents" / "implementer.md").exists()
    assert (python_project / ".claude" / "agents" / "code-reviewer.md").exists()
    assert (python_project / ".claude" / "agents" / "test-runner.md").exists()
    assert (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").exists()
    assert (python_project / ".claude" / "skills" / "ade-plan" / "SKILL.md").exists()
    assert (python_project / "CLAUDE.md").exists()


def test_init_does_not_generate_v3_artifacts(python_project: Path) -> None:
    """v4 should NOT generate CrewAI or Ollama artifacts."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    assert not (python_project / ".ade" / "config.yaml").exists()
    assert not (python_project / ".ade" / "crew").exists()
    assert not (python_project / ".ade" / "modelfiles").exists()
    # Default (claude) mode does not seed a pre-commit config.
    assert not (python_project / ".pre-commit-config.yaml").exists()


def test_init_creates_claude_md_with_pointer_block(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0

    content = (python_project / "CLAUDE.md").read_text()
    assert "<!-- ADE:START -->" in content
    assert "Agentic Development Environment" in content


def test_init_agent_definitions_have_model(python_project: Path) -> None:
    """Agent definitions should specify a model."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    implementer = (python_project / ".claude" / "agents" / "implementer.md").read_text()
    assert "model:" in implementer
    assert "sonnet" in implementer

    test_runner = (python_project / ".claude" / "agents" / "test-runner.md").read_text()
    assert "haiku" in test_runner


def test_init_skills_have_phase_content(python_project: Path) -> None:
    """Skills should contain phase instructions, renumbered 0–9."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])

    full = (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").read_text()
    assert "Phase 0" in full
    assert "Phase 9" in full or "RETROSPECTIVE" in full
    assert "Circuit Breaker" in full or "circuit breaker" in full.lower()

    plan = (python_project / ".claude" / "skills" / "ade-plan" / "SKILL.md").read_text()
    assert "PLAN" in plan or "plan" in plan


def test_doctor_reports_missing_tools(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    with patch("ade.cli._check_command", return_value=False):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_doctor_reports_all_ok(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 0


def test_doctor_flags_uninitialized_project(python_project: Path) -> None:
    """Doctor must FAIL on a project where `ade init` hasn't been run."""
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 1
    assert "FAIL" in result.output
    # Should hint at the recovery command
    assert "ade init" in result.output


def test_doctor_warns_on_missing_bootstrap_artifacts(python_project: Path) -> None:
    """Doctor should pass but warn when user-owned bootstrap files are removed."""
    import shutil

    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    # Remove the seeded docs/specs/ directory to simulate user cleanup
    shutil.rmtree(python_project / "docs" / "specs")

    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "WARN" in result.output


def test_status_no_tasks(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    result = runner.invoke(app, ["status", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "No" in result.output


def test_status_with_tasks(python_project: Path) -> None:
    tasks_dir = python_project / ".ade" / "tasks" / "test-task"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "status.md").write_text("Phase 4/10 - Implementing\n", encoding="utf-8")

    result = runner.invoke(app, ["status", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "test-task" in result.output


def test_init_generates_feature_spec_template(python_project: Path) -> None:
    """Feature spec template should be generated."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert (
        python_project / ".claude" / "skills" / "ade-research" / "references" / "feature-spec.md"
    ).exists()


def test_init_full_skill_has_exit_criteria(python_project: Path) -> None:
    """The main ade-full skill should have exit criteria for phases."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    content = (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").read_text()
    assert "Exit criteria:" in content
    assert "Hard requirement:" in content
    assert "Allowed fallback:" in content


def test_init_no_live_verification(python_project: Path) -> None:
    """No live-verification machinery remains anywhere in the full pipeline skill."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    skills_base = python_project / ".claude" / "skills"
    full = (skills_base / "ade-pipeline" / "SKILL.md").read_text()
    for token in ("Playwright", "docker compose", "localhost", "NO EXEMPTIONS", "/10"):
        assert token not in full, f"stale live-verify token in ade-pipeline/SKILL.md: {token}"
    assert (skills_base / "ade-intent" / "SKILL.md").exists()
    assert "07-verify" not in full


def test_init_generates_pr_reviewer_agent(python_project: Path) -> None:
    """The github PR reviewer agent should be scaffolded."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent_path = python_project / ".claude" / "agents" / "pr-reviewer.md"
    assert agent_path.exists()
    content = agent_path.read_text()
    assert "model:" in content
    assert "sonnet" in content
    assert "mcp__github__pull_request_read" in content
    assert "gh pr" in content


def test_init_generates_pr_review_command_and_skill(python_project: Path) -> None:
    """The /ade-pr-review command and its backing skill should be scaffolded."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    skill = python_project / ".claude" / "skills" / "ade-pr-review" / "SKILL.md"
    assert skill.exists()
    skill_content = skill.read_text()
    assert "pr-reviewer" in skill_content
    assert "max 3" in skill_content.lower() or "max **3**" in skill_content.lower()


def test_init_claude_mode_emits_settings_and_hooks(python_project: Path) -> None:
    result = runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    settings = python_project / ".claude" / "settings.json"
    assert settings.exists()
    assert "block-mixed-commit.py" in settings.read_text()
    assert (python_project / ".claude" / "hooks" / "_hooklib.py").exists()
    assert (python_project / ".claude" / "hooks" / "block-mixed-commit.py").exists()
    assert (python_project / ".claude" / "hooks" / "check-leftover-stub.py").exists()
    assert not (python_project / ".pre-commit-config.yaml").exists()
    assert (python_project / ".claude" / "hooks" / "check-escalation-paths.py").exists()
    assert "check-escalation-paths.py" in settings.read_text()


def test_init_rejects_unknown_agent(python_project: Path) -> None:
    result = runner.invoke(
        app, ["init", "--project-dir", str(python_project), "--agent", "cursor"]
    )
    assert result.exit_code != 0


def test_init_settings_merge_is_idempotent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    settings = json.loads((python_project / ".claude" / "settings.json").read_text())
    cmds = [h["command"] for block in settings["hooks"]["PreToolUse"] for h in block["hooks"]]
    assert (
        cmds.count("python .claude/hooks/block-mixed-commit.py --stdin-json --harness claude") == 1
    )


def test_init_settings_merge_preserves_existing(python_project: Path) -> None:
    settings_path = python_project / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}))
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    merged = json.loads(settings_path.read_text())
    assert merged["permissions"]["allow"] == ["Bash(ls)"]
    assert "PreToolUse" in merged["hooks"]


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


def test_init_generates_test_writer_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent = python_project / ".claude" / "agents" / "test-writer.md"
    assert agent.exists()
    content = agent.read_text()
    assert "model:" in content and "sonnet" in content
    assert "failing" in content.lower()
    assert "never" in content.lower() and "implementation" in content.lower()


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


def test_phase4_skill_describes_author_separation(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    phase4 = (python_project / ".claude" / "skills" / "ade-implement" / "SKILL.md").read_text()
    assert "test-writer" in phase4
    assert "RED" in phase4 or "failing test" in phase4.lower()
    assert "author separation" in phase4.lower() or "separate" in phase4.lower()


def test_init_seeds_ade_stack_file(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    stack = python_project / ".ade" / "ade-stack.md"
    assert stack.exists()
    content = stack.read_text()
    assert "build:" in content
    assert "lint:" in content
    assert "test:" in content
    # python block carries the detected commands
    assert "ruff check" in content


def test_init_ade_stack_seed_if_missing_preserves_edits(python_project: Path) -> None:
    stack = python_project / ".ade" / "ade-stack.md"
    stack.parent.mkdir(parents=True, exist_ok=True)
    stack.write_text("# my edited stack\n- test: make check\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited stack" in stack.read_text()


def test_review_skill_has_acceptance_coverage_gate(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (python_project / ".claude" / "skills" / "ade-review" / "SKILL.md").read_text()
    assert "acceptance-coverage gate" in review.lower()
    assert "Test adequacy" in review
    # acceptance is now the in-loop check; verify-phase wording is gone
    assert "verify phase" not in review.lower()


def test_no_stale_stack_references(python_project: Path) -> None:
    """No pre-G5 stack/verify token may survive in the generated tree (spec §5)."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    claude_dir = python_project / ".claude"
    docs = [
        p
        for p in claude_dir.rglob("*.md")
        if "vendored" not in p.parts
        and "grill-with-docs" not in p.parts  # vendored/grill keep their own wording
    ]
    docs.append(python_project / "AGENTS.md")  # canonical ADE instruction file lives here
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


def test_init_seeds_ade_routing_file(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    routing = python_project / ".ade" / "ade-routing.json"
    assert routing.exists()
    data = json.loads(routing.read_text())
    assert "escalation_globs" in data
    assert "architecture" in data["escalation_globs"]
    assert "keywords" in data


def test_init_ade_routing_seed_if_missing_preserves_edits(python_project: Path) -> None:
    routing = python_project / ".ade" / "ade-routing.json"
    routing.parent.mkdir(parents=True, exist_ok=True)
    routing.write_text('{"escalation_globs": {"architecture": ["*.custom"]}}\n')
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "*.custom" in routing.read_text()


def test_doctor_checks_escalation_hook(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    (python_project / ".claude" / "hooks" / "check-escalation-paths.py").unlink()
    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_init_generates_plan_reviewer_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent = python_project / ".claude" / "agents" / "plan-reviewer.md"
    assert agent.exists()
    content = agent.read_text()
    assert "model:" in content and "sonnet" in content
    assert "plan" in content.lower()
    assert "refute" in content.lower() or "adversarial" in content.lower()
    assert "acceptance criteria" in content.lower()
    # read-only: no Write/Edit/Bash in the tool list
    assert "Write" not in content and "Edit" not in content and "Bash" not in content
    # language-agnostic
    assert "@vitals" not in content


def test_init_generates_compounder_agent(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agent_path = python_project / ".claude" / "agents" / "compounder.md"
    assert agent_path.exists()
    content = agent_path.read_text()
    assert "model: sonnet" in content
    # read-only: no Write/Edit/Bash in the tools line
    assert "tools: [Read, Grep, Glob]" in content
    # contract terms
    assert "calibration" in content.lower()
    assert "Learning" in content
    assert "why this matters" in content.lower()
    assert "NO LEARNING" in content
    # never promotes severity by frequency
    assert "never" in content.lower() and "frequency" in content.lower()


def test_intent_skill_has_route_substep(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    intent = (python_project / ".claude" / "skills" / "ade-intent" / "SKILL.md").read_text()
    assert "0d — Route" in intent or "0d - Route" in intent
    for tier in ("trivial", "standard", "architecture"):
        assert tier in intent
    assert "ade-routing.json" in intent
    assert "forced-escalation" in intent.lower() or "escalation" in intent.lower()


def test_ade_full_describes_routing_and_tiers(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    full = (python_project / ".claude" / "skills" / "ade-pipeline" / "SKILL.md").read_text()
    for tier in ("trivial", "standard", "architecture"):
        assert tier in full
    assert "Plan Soundness Review" in full
    assert "skipped for" in full.lower() or "skip for" in full.lower()  # masking annotations
    assert "ade-routing.json" in full or "forced-escalation" in full.lower()


def test_init_seeds_learnings_dir(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    readme = python_project / "docs" / "learnings" / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "Why this matters" in content
    assert "Learning" in content
    # boundary vs ADR is spelled out so future agents pick the right artifact
    assert "ADR" in content


def test_init_learnings_seed_if_missing_preserves_edits(python_project: Path) -> None:
    readme = python_project / "docs" / "learnings" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("# my edited learnings index\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited learnings index" in readme.read_text()


def test_init_seeds_review_calibration(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    corpus = python_project / "docs" / "review-calibration.md"
    assert corpus.exists()
    content = corpus.read_text()
    assert "finding-class" in content.lower()
    assert "Frequency" in content
    assert "Severity" in content


def test_init_review_calibration_seed_if_missing_preserves_edits(python_project: Path) -> None:
    corpus = python_project / "docs" / "review-calibration.md"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text("# my edited corpus\n")
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert "my edited corpus" in corpus.read_text()


def test_doctor_checks_compound_artifacts(python_project: Path) -> None:
    """Doctor passes but WARNs when the seeded compound artifacts are removed."""
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    (python_project / "docs" / "review-calibration.md").unlink()

    with patch("ade.cli._check_command", return_value=True):
        result = runner.invoke(app, ["doctor", "--project-dir", str(python_project)])
    assert result.exit_code == 0
    assert "WARN" in result.output
    assert "review-calibration" in result.output


def test_review_reads_calibration(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (python_project / ".claude" / "skills" / "ade-review" / "SKILL.md").read_text()
    assert "docs/review-calibration.md" in review
    assert "fresh" in review.lower()


def test_review_persists_output(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    review = (python_project / ".claude" / "skills" / "ade-review" / "SKILL.md").read_text()
    assert ".ade/tasks/<task-id>/review.md" in review
    assert "even when" in review.lower()


def test_retro_skill_describes_codify_step(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    retro = (python_project / ".claude" / "skills" / "ade-retro" / "SKILL.md").read_text()
    assert "Codify" in retro
    assert "docs/learnings/" in retro
    assert "docs/review-calibration.md" in retro
    assert "compounder" in retro
    # conditional learning + trivial exclusion are explicit
    assert "NO LEARNING" in retro or "no Learning" in retro
    assert "trivial" in retro.lower()


def test_research_reads_learnings(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    research = (python_project / ".claude" / "skills" / "ade-research" / "SKILL.md").read_text()
    assert "docs/learnings/" in research


def test_agents_md_describes_compound_loop(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    agents_md = (python_project / "AGENTS.md").read_text()
    assert "docs/learnings/" in agents_md
    assert "review-calibration.md" in agents_md
    assert "Codify" in agents_md


def test_config_lives_in_dot_ade(python_project: Path) -> None:
    runner.invoke(app, ["init", "--project-dir", str(python_project)])
    assert (python_project / ".ade" / "ade-routing.json").exists()
    assert (python_project / ".ade" / "ade-stack.md").exists()
    assert not (python_project / ".claude" / "ade-routing.json").exists()
    assert not (python_project / ".claude" / "ade-stack.md").exists()
