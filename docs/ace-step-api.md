# ACE-Step — song generation that fits beside everything else

**lyrics → a full song with vocals**, in under 10 seconds on an RTX 3090, using
under 5 GB of VRAM.

## Why not YuE

YuE was the original candidate and it is the wrong model for a stack that shares
its GPU.

| | YuE | **ACE-Step 1.5** |
| --- | --- | --- |
| VRAM | 24 GB, BF16 required | **~4.7 GB** (2B variant) |
| Speed (RTF, RTX 4090) | 0.083× — *slower than realtime* | **15.63×** — 2–8 s per track |
| Parameters | 7B | 3.5B |
| Licence | Apache-2.0 | Apache-2.0 |

Two things matter here. First, **188× faster** on the same card. Second, and more
decisively for puente: YuE needs 24 GB of BF16, which is the whole card, leaving
nothing for ComfyUI, Voicebox or the LLM. ACE-Step's 2B model fits in what a
shared card has spare.

A song generator that has to be switched off to use anything else is not a
service. That is the whole criterion.

The XL variant (4B DiT, ~9 GB, needs ≥12 GB free with offload) is available for
hosts with room. On this box it does not.

## Why it is its own service, not a ComfyUI node

Not for tidiness — a version conflict:

```
ACE-Step 1.5 pins   torch 2.10.0+cu128   (pyproject.toml, linux x86_64)
ComfyUI image ships torch 2.6.0+cu124
```

They cannot share a venv. Installing ACE-Step into ComfyUI's environment would
break one or the other, and ComfyUI is load-bearing for image and video. A
separate container gets its own torch, its own GPU pin and its own healthcheck.

The official ComfyUI node (`ace-step/ACE-Step-ComfyUI`, MIT) is a **client** of
this server rather than a self-contained node, so it can be pointed here later
without changing anything in this service.

## Config

```yaml
  ace_step:
    enabled: true
    port: 8002
    gpu: GPU-<uuid>          # pin it; a contended card cannot guess
    variant: 2b              # 2b = acestep-v15-turbo (~4.7GB) | xl = acestep-v15-xl-turbo (~9GB)
    resident: false          # load per request, give it back. See below.
    lm_model: acestep-5Hz-lm-1.7B
    lm_backend: pt           # pt is lighter; vllm is faster but claims VRAM
    build_ref: <commit-sha>  # pin it — a branch makes the image non-reproducible
```

`resident: false` disables the 5Hz language model entirely
(`ACESTEP_INIT_LLM=false`). With it off you lose thinking mode, CoT captioning
and sample generation — and gain the VRAM back. On a card shared with ComfyUI
that is the right default; it is why the LM follows `resident` rather than
defaulting on.

### The variant map is explicit

Upstream names the 2B family `acestep-v15-turbo` and the 4B family
`acestep-v15-xl-turbo`. There is no `acestep-v15-2b-turbo`. The service maps
puente's `variant` through a dict rather than interpolating it into a string,
because a config name that does not exist starts cleanly and then fails on the
first generation request — with nothing to indicate the name was the problem.
`tests/test_ace_step.py` pins both against the names in upstream's README.

## VRAM

This is the service that makes the residency policy concrete. Every prior
load/unload collision on this host has come from GPU 1 (the 16 GB card) holding
~13 GB between Voicebox and Ollama's classroom preload. ACE-Step's ~4.7 GB does
not fit there alongside them, so:

- **Pin it deliberately** (`gpu:`), and
- **Leave `resident: false`** unless the card has room.

Adding it without doing both is how the 2026-10-10 boot race happens again.

## Not yet run

Landed and unit-tested; **not** yet built or run on this host — the first build
compiles the image from upstream's git context (torch + CUDA, expect 10–20 min)
and downloads checkpoints. Verified so far: every environment variable comes
from upstream's `.env.example`, both config-path names exist upstream, and the
compose fragment generates cleanly.