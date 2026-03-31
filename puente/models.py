"""Pydantic models for puente.yml configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class OllamaInstance(BaseModel):
    name: str = "primary"
    gpu: int | None = None
    port: int = 11434
    models: list[str] = Field(default_factory=lambda: ["llama3.1:8b-q4_k_m"])


class ServiceConfig(BaseModel):
    enabled: bool = True
    install_method: Literal["docker", "native", "external"] = "docker"
    port: int | None = None
    gpu: int | None = None
    managed: bool = True  # False = coexist with existing install
    environment: dict[str, str] = Field(default_factory=dict)


class OllamaConfig(ServiceConfig):
    install_method: Literal["docker", "native", "external"] = "native"
    instances: list[OllamaInstance] = Field(
        default_factory=lambda: [OllamaInstance()]
    )


class StackConfig(BaseModel):
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    open_webui: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3000)
    )
    speaches: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8000, enabled=False)
    )
    comfyui: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(
            port=8188, install_method="docker", enabled=False
        )
    )
    searxng: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8888)
    )
    vane: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3005, enabled=False)
    )
    anythingllm: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3001, enabled=False)
    )
    open_notebook: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8502, enabled=False)
    )
    stirling_pdf: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8089, enabled=False)
    )
    excalidraw: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3333, enabled=False)
    )
    citesight: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3010, enabled=False)
    )
    jupyter: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8888, enabled=False)
    )


class PuenteConfig(BaseModel):
    data_dir: Path = Path("~/.puente")
    services: StackConfig = Field(default_factory=StackConfig)

    def resolved_data_dir(self) -> Path:
        return self.data_dir.expanduser()


CONFIG_FILE = "puente.yml"


def load_config(path: Path | None = None) -> PuenteConfig:
    """Load config from puente.yml, or return defaults if not found."""
    config_path = path or Path(CONFIG_FILE)
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text())
        return PuenteConfig.model_validate(raw or {})
    return PuenteConfig()


def save_config(config: PuenteConfig, path: Path | None = None) -> Path:
    """Write config to puente.yml."""
    config_path = path or Path(CONFIG_FILE)

    # Convert to dict, using aliases for yaml-friendly keys
    data = config.model_dump(mode="json")

    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return config_path
