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

- Builds on `ubuntu:22.04` with exactly one package (`libmicrohttpd12`) for the **CPU**
  path. No Python. The whole engine is ~7 MB.
- CPU inference is correct; the REST API and bundled GUI both work.
- Quantisation (`ncconvert -q bf8|bf4|bf3`) runs on CPU in under a second.
- Multiple instances run concurrently — the one-model limit is per process, not per host.

## GPU: unsupported on this hardware (not a bug)

The docs require **an Ampere, ADA or Hopper GPU with CUDA 11.x or 12.x**, and note that
ts_server needs **cuBLASLt from the CUDA toolkit**.

This box has RTX 2060 Supers — **Turing, sm_75**, a generation older than Ampere
(sm_80/86) — on driver 595 (CUDA 13.2). `ts_test --cuda` fails at `cuModuleLoadData`
with "Could not load cuda module data", on bare metal as well as in a container. That is
the expected result of running a kernel image built for sm_80+ on an sm_75 card.

Retested with a real CUDA 12 toolkit on `LD_LIBRARY_PATH` — identical failure. So the
GPU architecture, not the CUDA version, is the binding constraint.

> **Correction:** an earlier version of this file claimed "no CUDA toolkit needed",
> reasoning from `ldd libnc_cuda.so` showing only `libcuda.so.1`. That was wrong —
> `libcublasLt.so` is `dlopen`'d at runtime (see `load_cublas_lt` in its strings).
> The Dockerfile below therefore only supports the CPU path.

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
