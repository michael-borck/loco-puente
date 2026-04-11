"""MusicGen — multi-model audio generation via TTS WebUI (Docker, GPU)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class MusicGenService(ServiceBase):
    name = "musicgen"
    description = "Audio generation: MusicGen, AudioGen, Bark, Tortoise, etc."
    default_port = 3000
    install_method = "docker"
    # We previously tried building Meta's audiocraft from source, but
    # audiocraft pins av==11.0.0 which only works against ffmpeg 5.0/5.1,
    # and no major LTS distro ships that exact range — making the source
    # build a moving-target rabbit hole.
    #
    # Instead, use Ashley Kleynhans's actively-maintained TTS WebUI image
    # (https://github.com/ashleykleynhans/tts-generation-docker, GPL-3.0),
    # which bundles MusicGen + AudioGen + Bark + Tortoise + StyleTTS2 +
    # several others behind a single Gradio UI on port 3000. We pin to a
    # specific release tag rather than :latest so upstream changes don't
    # silently re-pull a different image under us — bump this tag in
    # follow-up commits when adopting newer releases.
    docker_image = "ashleykza/tts-webui:5.1.3"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        # The image exposes several ports internally (3005 react beta UI,
        # 7777 code-server, 8000 app manager, 8888 jupyter, 2999 file
        # uploader). We only publish 3000 — the main TTS WebUI — because
        # the other surfaces overlap with services puente already runs
        # (jupyter), or aren't relevant to a chat-style PoC.
        fragment: dict[str, Any] = {
            "musicgen": {
                "image": self.docker_image,
                "container_name": "puente-musicgen",
                "ports": [f"{port}:3001"],
                "volumes": [
                    f"{data_dir}/musicgen:/workspace",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["musicgen"]["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "device_ids": [str(config.gpu)],
                                "capabilities": ["gpu"],
                            }
                        ]
                    }
                }
            }

        return fragment
