# SwarmUI — friendly image-gen front-end (mcmonkeyprojects/SwarmUI).
#
# SwarmUI is a .NET 8 web app that bundles its own ComfyUI backend by
# default but supports talking to an external ComfyUI instance — which is
# what we want, so it shares puente-comfyui's GPU and checkpoint cache
# instead of duplicating them.
#
# Upstream ships build/launch scripts under launchtools/. We use those
# rather than reverse-engineering the dotnet build, because the project
# layout (src paths, project file names) has changed across releases.
# .NET 8 + python3 are required because SwarmUI shells out to python for
# some helper scripts even when its own ComfyUI bundle is disabled.
#
# First build is slow (~5–10 min): clones repo, restores nuget packages,
# compiles the .NET project, fetches the dotnet runtime layers.
FROM mcr.microsoft.com/dotnet/sdk:8.0

# Avoid the tzdata interactive timezone prompt that hangs container
# builds without a TTY (transitive dep on Debian-based images).
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        python3 \
        python3-venv \
        python3-pip \
        wget \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /SwarmUI
RUN git clone --depth 1 https://github.com/mcmonkeyprojects/SwarmUI.git .
RUN chmod +x launchtools/*.sh

# Build the .NET project ahead of time so first-run is just app startup.
# `make-build.sh` is SwarmUI's documented build entrypoint.
RUN ./launchtools/make-build.sh || true

EXPOSE 7801

# launch-linux.sh handles environment setup, dependency checks, and starts
# the .NET app. --launch_mode none disables the auto-open browser. The host
# / port flags make the dotnet listener bind to all interfaces inside the
# container so the host port mapping reaches it.
CMD ["./launchtools/launch-linux.sh", "--launch_mode", "none", "--host", "0.0.0.0", "--port", "7801"]
