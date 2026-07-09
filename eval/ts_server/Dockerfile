FROM ubuntu:22.04

# ts_server links only libmicrohttpd + libstdc++ + glibc (>= 2.27).
# The CUDA backend (libnc_cuda.so) links ONLY libcuda.so.1 (the driver stub),
# which the NVIDIA container runtime injects. No CUDA toolkit needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmicrohttpd12 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG TARBALL=ts_server_free-2025-03-09.tar.gz
COPY ${TARBALL} /tmp/ts.tar.gz
RUN mkdir -p /opt/ts_server \
    && tar xzf /tmp/ts.tar.gz -C /opt/ts_server --strip-components=1 \
    && rm /tmp/ts.tar.gz

WORKDIR /opt/ts_server
ENV LD_LIBRARY_PATH=/opt/ts_server

# Let the driver JIT PTX for whatever GPU is present (Turing 7.5 .. Blackwell).
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8080
VOLUME ["/models"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
