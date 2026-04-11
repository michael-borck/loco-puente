# Fooocus — opinionated SDXL image-gen UI (lllyasviel/Fooocus).
#
# Upstream ships installer scripts but no Docker image. We clone the repo,
# install its pinned Python deps, and run their `entry_with_update.py`
# launch script which auto-pulls Juggernaut XL and the SDXL refiner on
# first use into models/checkpoints/. Mount /content/Fooocus/models and
# /content/Fooocus/outputs as volumes to persist downloads + generations.
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Avoid the tzdata interactive timezone prompt that hangs container
# builds without a TTY (transitive dep of several X11/glib packages).
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /content
RUN git clone --depth 1 https://github.com/lllyasviel/Fooocus.git
WORKDIR /content/Fooocus

# Pinned requirements file is the supported install path per Fooocus README.
RUN pip install --no-cache-dir -r requirements_versions.txt

EXPOSE 7865
CMD ["python", "entry_with_update.py", "--listen", "0.0.0.0", "--port", "7865"]
