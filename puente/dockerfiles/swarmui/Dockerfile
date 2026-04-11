# SwarmUI — friendly image-gen front-end (mcmonkeyprojects/SwarmUI).
#
# This Dockerfile mirrors SwarmUI's own launchtools/StandardDockerfile.docker,
# adjusted for a self-contained build (git clone inside the Dockerfile
# rather than relying on a COPY from the user's local SwarmUI checkout).
# The upstream entrypoint — docker-standard-inner.sh — handles the dotnet
# build at container start time, which is why we don't pre-build here.
#
# First container start is slow (~2–5 min): dotnet restore + compile the
# SwarmUI project inside the running container. Subsequent starts reuse
# the built binaries in the container's layer.
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim

# Avoid the tzdata interactive timezone prompt during apt installs.
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

ARG UID=1000

# Runtime + build dependencies required by SwarmUI's upstream Dockerfile:
# python3.11 for backend scripts, build-essential for any native deps,
# ffmpeg for media handling, libglib2.0-0 + libgl1 for controlnet
# preprocessors.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget \
        build-essential \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3-pip \
        ffmpeg \
        libglib2.0-0 \
        libgl1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pull SwarmUI into /SwarmUI. The upstream Dockerfile uses COPY from the
# checked-out repo; we git clone instead so this Dockerfile is
# self-contained and builds from a clean environment.
RUN git clone --depth 1 https://github.com/mcmonkeyprojects/SwarmUI.git /SwarmUI

# Allow the build UID to own the SwarmUI tree (upstream pattern).
RUN chown -R $UID:$UID /SwarmUI

# Stupidproof git calls that happen from inside the container (upstream).
RUN git config --global --add safe.directory '*'

# Ensure a user exists for the given UID so docker-standard-inner.sh
# can drop privileges cleanly.
RUN useradd -u $UID -m swarmui || true

# If any built binaries slipped into the clone, wipe them — SwarmUI
# rebuilds inside the container so extensions link correctly.
RUN rm -rf /SwarmUI/src/bin /SwarmUI/src/obj

EXPOSE 7801

# SwarmUI's canonical container entrypoint. It handles dotnet build,
# Python venv setup, and SwarmUI startup. We pass host/port overrides
# via SWARMUI_LAUNCH_MODE so the binary listens on all interfaces
# inside the container.
ENTRYPOINT ["bash", "/SwarmUI/launchtools/docker-standard-inner.sh"]
