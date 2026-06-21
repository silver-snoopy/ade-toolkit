"""Build-time location-verification test.

Pins each harness's structural constants (skills_dirs + memory_file) against the
verified reference in docs/harness-locations.md.  If a vendor silently renames a
path, this test fails CI with a pointer to refresh the reference.

IMPORTANT: EXPECTED mirrors docs/harness-locations.md (Task C0).
Update BOTH together whenever a vendor changes paths.
"""

from __future__ import annotations

from ade.harnesses import TARGETS

# Mirror of docs/harness-locations.md (C0). Update BOTH together when a vendor changes paths.
# Codex uses .agents/skills/ ONLY — no .codex/skills/ (confirmed C0, cross-harness summary).
EXPECTED = {
    "claude": {"skills": ".claude/skills", "memory": "CLAUDE.md"},
    "gemini": {"skills": ".gemini/skills", "memory": "GEMINI.md"},
    "copilot": {"skills": ".github/skills", "memory": ".github/copilot-instructions.md"},
    "codex": {"skills": ".agents/skills", "memory": "AGENTS.md"},
}


def test_every_target_matches_verified_locations() -> None:
    assert set(TARGETS) == set(EXPECTED), (
        f"TARGETS keys {set(TARGETS)} differ from EXPECTED {set(EXPECTED)}; "
        "update both EXPECTED and docs/harness-locations.md"
    )
    for name, exp in EXPECTED.items():
        t = TARGETS[name]
        assert exp["skills"] in t.skills_dirs, (
            f"{name}: skills dir '{exp['skills']}' not in {t.skills_dirs}; "
            "path drifted from docs/harness-locations.md"
        )
        assert t.memory_file == exp["memory"], (
            f"{name}: memory_file '{t.memory_file}' != '{exp['memory']}'; "
            "drifted from docs/harness-locations.md"
        )
        assert ".agents/skills" in t.skills_dirs, (
            f"{name}: shared convergence dir '.agents/skills' missing from {t.skills_dirs}"
        )


def test_codex_is_degraded_tier() -> None:
    assert TARGETS["codex"].supports_subagents is False
