"""ADE configuration models and generation logic."""

from __future__ import annotations

import yaml
from pydantic import BaseModel, Field

from ade.detect import ProjectInfo


class ModelConfig(BaseModel):
    name: str
    provider: str = "ollama"
    context_window: int = 131072
    temperature: float = 0.1


class ModelsConfig(BaseModel):
    primary: ModelConfig = Field(default_factory=lambda: ModelConfig(name="gemma4:31b"))
    test_generator: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            name="qwen2.5-coder:14b", context_window=65536, temperature=0.2
        )
    )
    fallback: ModelConfig = Field(default_factory=lambda: ModelConfig(name="qwen2.5-coder:32b"))
    mode: str = "hot-swap"


class OrchestrationConfig(BaseModel):
    max_phase_iterations: int = 3
    max_total_iterations: int = 9
    max_phase_duration_minutes: int = 30
    human_checkpoints: list[str] = Field(
        default_factory=lambda: ["after_plan", "after_final_review"]
    )


class WorktreeConfig(BaseModel):
    base_dir: str = ".ade/worktrees"
    cleanup_after_merge: bool = True
    branch_prefix: str = "ade/"


class ScannerToggle(BaseModel):
    enabled: bool = False


class PrettierConfig(BaseModel):
    enabled: bool = False
    write: bool = True


class ScanningConfig(BaseModel):
    pre_commit: bool = True
    semgrep: ScannerToggle = Field(default_factory=lambda: ScannerToggle(enabled=True))
    ruff: ScannerToggle = Field(default_factory=ScannerToggle)
    eslint: ScannerToggle = Field(default_factory=ScannerToggle)
    prettier: PrettierConfig = Field(default_factory=PrettierConfig)
    detect_secrets: ScannerToggle = Field(default_factory=lambda: ScannerToggle(enabled=True))


class FallbackTriggersConfig(BaseModel):
    consecutive_tool_failures: int = 3
    qa_fix_failures: int = 3
    empty_responses: int = 2


class ProjectConfig(BaseModel):
    name: str
    languages: list[str] = Field(default_factory=list)
    test_commands: dict[str, str] = Field(default_factory=dict)
    build_command: str | None = None


class LoggingConfig(BaseModel):
    level: str = "info"
    format: str = "structured"
    retention_days: int = 30


class AdeConfig(BaseModel):
    version: str = "2.0"
    project: ProjectConfig
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    worktree: WorktreeConfig = Field(default_factory=WorktreeConfig)
    scanning: ScanningConfig = Field(default_factory=ScanningConfig)
    fallback_triggers: FallbackTriggersConfig = Field(default_factory=FallbackTriggersConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def to_yaml(self) -> str:
        """Serialize config to YAML string."""
        data = self.model_dump(exclude_none=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


def build_config(info: ProjectInfo) -> AdeConfig:
    """Build ADE config from detected project info."""
    scanning = ScanningConfig(
        ruff=ScannerToggle(enabled="python" in info.languages),
        eslint=ScannerToggle(
            enabled="typescript" in info.languages or "javascript" in info.languages
        ),
        prettier=PrettierConfig(
            enabled="typescript" in info.languages or "javascript" in info.languages
        ),
    )

    return AdeConfig(
        project=ProjectConfig(
            name=info.project_name,
            languages=info.languages,
            test_commands=info.test_commands,
        ),
        scanning=scanning,
    )
