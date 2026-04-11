# MusicGen — Meta's AudioCraft + the bundled Gradio demo app.
#
# AudioCraft is published as a Python package by facebookresearch but ships
# no Docker image. The audiocraft repo includes a Gradio demo at
# `demos/musicgen_app.py` which we use as the user-facing UI. Models
# (musicgen-small/medium/large/melody) are downloaded from Hugging Face on
# first use and cached under /root/.cache/huggingface (mount a volume there
# to persist across restarts).
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# ffmpeg pulls in tzdata as a transitive dep, which runs an interactive
# timezone picker inside the container build and hangs forever without
# a TTY. Force the non-interactive frontend with a pre-set timezone so
# the install proceeds unattended.
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Clone audiocraft for the bundled demo app + install in editable mode so
# the demo's relative imports resolve.
RUN git clone --depth 1 https://github.com/facebookresearch/audiocraft.git /audiocraft
WORKDIR /audiocraft
RUN pip install --no-cache-dir -e . gradio

# Make Gradio bind to all interfaces inside the container so the host port
# mapping reaches it.
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

EXPOSE 7860
CMD ["python", "demos/musicgen_app.py"]
