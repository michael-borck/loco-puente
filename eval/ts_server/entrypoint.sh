#!/bin/sh
set -eu

# The FREE version accepts exactly ONE model definition. So we generate the
# config at start-up: switching task == restarting with a different TS_MODEL.
#
#   TS_MODEL       logical name used in the REST path /v1/engines/<name>/...
#   TS_MODEL_FILE  the .bin under /models
#   TS_MODEL_FILE2 second file (parler-tts needs dac_mono.bin)
#   TS_CUDA        true|false
#   TS_DEVICE_INDEX  which GPU, as seen *inside* the container
#   TS_FULL_MEMORY false => allocate GPU mem on demand (share a card)

TS_MODEL="${TS_MODEL:-gpt2_117M}"
TS_MODEL_FILE="${TS_MODEL_FILE:-gpt2_117M.bin}"
TS_CUDA="${TS_CUDA:-false}"
TS_DEVICE_INDEX="${TS_DEVICE_INDEX:-0}"
TS_FULL_MEMORY="${TS_FULL_MEMORY:-false}"
TS_PORT="${TS_PORT:-8080}"
TS_GUI="${TS_GUI:-true}"
TS_KV_CACHE_COUNT="${TS_KV_CACHE_COUNT:-4}"
TS_KV_CACHE_SIZE="${TS_KV_CACHE_SIZE:-1e9}"

if [ ! -f "/models/${TS_MODEL_FILE}" ]; then
    echo "FATAL: /models/${TS_MODEL_FILE} not found." >&2
    echo "Download it, e.g.:" >&2
    echo "  curl -L -o models/${TS_MODEL_FILE} \\" >&2
    echo "    https://huggingface.co/fbellard/ts_server/resolve/main/${TS_MODEL_FILE}" >&2
    exit 1
fi

model_entry="{ name: \"${TS_MODEL}\", filename: \"/models/${TS_MODEL_FILE}\""
if [ -n "${TS_MODEL_FILE2:-}" ]; then
    model_entry="${model_entry}, filename2: \"/models/${TS_MODEL_FILE2}\""
fi
if [ -n "${TS_N_CTX:-}" ]; then
    model_entry="${model_entry}, n_ctx: ${TS_N_CTX}"
fi
model_entry="${model_entry} }"

cuda_block=""
if [ "${TS_CUDA}" = "true" ]; then
    cuda_block="  cuda: true,
  device_index: ${TS_DEVICE_INDEX},
  full_memory: ${TS_FULL_MEMORY},"
    [ -n "${TS_MAX_MEMORY:-}" ] && cuda_block="${cuda_block}
  max_memory: ${TS_MAX_MEMORY},"
fi

cat > /tmp/ts_server.cfg <<EOF
{
${cuda_block}
  kv_cache_max_count: ${TS_KV_CACHE_COUNT},
  kv_cache_size: ${TS_KV_CACHE_SIZE},
  models: [
    ${model_entry},
  ],
  local_port: ${TS_PORT},
  bind_addr: "0.0.0.0",
  gui: ${TS_GUI},
  log_start: true,
  log_filename: "/dev/stdout",
}
EOF

echo "--- ts_server.cfg ---"
cat /tmp/ts_server.cfg
echo "---------------------"

exec /opt/ts_server/ts_server "$@" /tmp/ts_server.cfg
