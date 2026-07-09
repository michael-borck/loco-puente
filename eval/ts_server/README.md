# TextSynth Server — evaluation (not adopted)

Container scaffolding for Fabrice Bellard's [TextSynth Server](https://bellard.org/ts_server/),
evaluated as a lightweight alternative to parts of the Puente stack.

**Outcome: not adopted.** Kept for reference and in case upstream revives.

## Why not

- **Model library is frozen.** The server binary carries a hard-coded architecture
  list (`bert bloom falcon gpt2 gptj mistral parler_tts phi3 qwen2 rwkv whisper`).
  Qwen3 and Gemma are absent, and patching the open Python converter does not help —
  the gate is inside the closed binary. Last release: 2025-03-09.
- **No SDXL.** `sd_convert.py` emits only `sd` / `sd2` (Stable Diffusion 1.x / 2.1),
  and `ts_sd` contains no LoRA support. Juggernaut-XL and friends cannot run, which
  rules it out for student-facing image generation.
- **One model per process.** The free version accepts a single `models: []` entry, so
  serving chat + image + speech means one container each.
- **Licence.** Non-commercial only, and redistribution is prohibited — so no image can
  ever be published, and university teaching use needs the author's written approval.

## What did work

- Builds on `ubuntu:22.04` with exactly one package (`libmicrohttpd12`). `libnc_cuda.so`
  links only `libcuda.so.1` — hand-written kernels against the driver API, no
  cudart/cuBLAS/cuDNN, no Python. The whole engine is ~7 MB.
- CPU inference is correct; the REST API and bundled GUI both work.
- Quantisation (`ncconvert -q bf8|bf4|bf3`) runs on CPU in under a second.
- Multiple instances run concurrently — the one-model limit is per process, not per host.

**CUDA does not work on driver 595** (`cuModuleLoadData` → "Could not load cuda module
data"). This reproduces on bare metal with the vendor's own `ts_test`, so it is not a
container problem. Likely the CUDA 13 JIT rejecting the binary's kernel image, but the
actual `CUresult` was never captured — treat that as a hypothesis.

## Building

The binaries are **not** in this repo and must not be redistributed. Download the
tarball yourself into this directory first:

    curl -O https://bellard.org/ts_server/ts_server_free-2025-03-09.tar.gz

Models go in `models/` (gitignored). Fetch and **verify** them — Hugging Face serves
these `.bin` files gzip-encoded, and a naive `curl -sO` yields a truncated file that
loads without error and emits gibberish:

    mkdir -p models
    curl -sL -H 'Accept-Encoding: identity' -o models/gpt2_117M.bin \
      "https://huggingface.co/fbellard/ts_server/resolve/main/gpt2_117M.bin?download=true"
    sha256sum models/gpt2_117M.bin
    curl -s https://bellard.org/ts_server/sha256.txt | grep 'gpt2_117M.bin$'

Then:

    docker compose up --build ts-text

Switching task means restarting with a different `TS_MODEL` — see `entrypoint.sh`,
which generates the single-model config from environment variables.
