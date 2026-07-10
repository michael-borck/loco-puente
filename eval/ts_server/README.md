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

## GPU: crashes inside cuBLASLt on supported hardware (a real bug)

The docs require **an Ampere, ADA or Hopper GPU with CUDA 11.x or 12.x**, and note that
ts_server needs **cuBLASLt from the CUDA toolkit**.

**On the Turing 2060 Supers (sm_75)** — a generation older than Ampere — `ts_test --cuda`
failed at `cuModuleLoadData` with "Could not load cuda module data". Expected: a kernel
image built for sm_80+ cannot run on sm_75. Retested with a real CUDA 12 toolkit on
`LD_LIBRARY_PATH` — identical failure, so architecture, not CUDA version, was the
binding constraint. **This was never a bug.**

**On the RTX 3090 (Ampere, sm_86)** — the hardware the docs ask for — that gate passes:
ts_server opens `/dev/nvidia0`, `dlopen`s `libcublasLt.so`, and allocates ~1.6 GB of
weights. It then **segfaults on the first forward pass**, before emitting a token, inside
`cublasLtMatmulAlgoGetHeuristic` — reached from `nc_matmul_add2` in `libnc.so`.

**Root cause: ts_server passes `Cdesc = NULL`.** Interposing `dlsym` (see
`cublaslt-hook.c`; full log in `crash-trace.txt`) shows that for `gpt2_117M`
(`n_layer=12`) the first **48** heuristic calls — 12 layers × 4 matmuls — all return
`rc=0, returnAlgoCount=4`. The **49th** is handed a null `Cdesc` and dereferences it:

```
Cdesc = (nil)      # all other args valid; cublasLtCreate returned rc=0
```

Call 49 is the final projection to the vocabulary (`d_model=768` → `50257`) — the one
matmul with no bias to accumulate. `cublasLt.h` documents `Cdesc` as an `[in]` handle
with no null allowance.

This is **structural, not hardware-specific** — it should fire on any GPU, including an
A100. Evidence:

| Hypothesis | Test | Result |
|---|---|---|
| cuBLASLt version too new (12.9) | rerun against **12.1** (torch's wheel, inside documented 11.x/12.x) | **identical segfault** — not the version |
| driver 595 / CUDA 13.2 too new | torch fp16 matmul (dispatches via cuBLASLt) on same 3090 + driver | **works** — but weaker than it looks (different heuristic path) |
| card unsupported | 3090 is sm_86, Ampere | **satisfies the docs** |
| the interposer causes it | run with no `LD_PRELOAD` | **same crash**, same faulting address |
| a race / memory corruption | repeat runs, vary `-l` | **always call 49** — fully deterministic |

**Do not downgrade the driver to chase it** — the 12.1 test shows it would not help, and
it would destabilise the working torch/ComfyUI stack.

**Reproducing:** `-l N` is required (default max output length is 0 tokens, so the crash
hides behind an apparently-clean run), and do not pipe to `tail` — it masks exit 139.

This does not change the verdict below: no SDXL, so no adoption today. But SDXL+LoRA
would make it compelling, which is why `email-draft.md` asks — and why the GPU path
mattering again means the bug is worth reporting.

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
