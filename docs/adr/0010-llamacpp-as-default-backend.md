# 0010 — llama.cpp becomes the default LLM backend; Ollama retires

**Status:** Accepted (2026-10-10) — prototype landed, Ollama still the default

## Context

The PoC box has 70 GB of models on disk and, at rest, about 266 MiB of VRAM in
use. The models fit on disk comfortably; the problem is never having a policy
about what is *resident*. GPU services on this host are:

| Card | Services | Concurrent weight |
| --- | --- | --- |
| GPU 0, RTX 3090, 24 GB | speaches, comfyui, swarmui | comfortable |
| GPU 1, RTX 4060 Ti, 16 GB | voicebox, ollama classroom preload | ~13 GB of 16 GB — tight |

Every load/unload collision so far has come from that second row: the 2026-10-10
reboot lost a race between `gemma4:12b` and Voicebox's weights, taking both down.
The fix used retries, which is honest but not a solution — a card holding 13 GB of
weights has no headroom for a third consumer.

Ollama gives no control over placement. It loads a whole model onto a card and
sets a TTL, and that is the entire vocabulary. That is workable while a box runs
one model at a time and stops being workable the moment a second service wants the
same card.

## Decision

**llama.cpp becomes the LLM backend; Ollama retires.** Not because llama.cpp is a
better default engine — it is not, Ollama is far easier to operate — but for one
capability none of the alternatives has.

`--cpu-moe N` keeps a MoE model's routed experts in system RAM while attention,
KV cache and shared experts stay in VRAM. Experts activate on only a few percent
of tokens, so the RAM path is not a bottleneck. The result, measured by others on
consumer cards: a 21 GB MoE serving in 10.2 GB of VRAM, and a 35B MoE occupying
*less* VRAM than an 8B dense model.

**Ollama, vLLM and SGLang all lack this.** vLLM and SGLang are architected around
tensor parallelism and have no expert-aware CPU offload. So the proposal to "move
to vLLM" and the desire for MoE expert offload are mutually exclusive, and that
is the finding that decides this.

Consequences accepted:

- GGUF instead of Ollama's model format. Hugging Face conversion is a step, and
  it is a real cost for a novice audience.
- No `ollama pull`. Models are files in a directory, or fetched from the Hub by
  `hf_repo`/`hf_file`. Operational work Ollama did for free becomes explicit.
- llama-server is single-model, so several models means several instances. The
  config shape mirrors Ollama's (`instances:` with a name, port and model)
  specifically so the two stay swappable.

The config keeps `n_gpu_layers` as the coarse dial (bound the card explicitly) and
`cpu_moe` as the fine one. Both are asserted in tests, because a wrong flag here
fails *silently* — `-ncmoe` on a dense model is accepted and does nothing, and an
over-large `-ngl` is silently clamped.

## Consequences

- `puente doctor` validates llama.cpp's per-instance GPU pins. They live inside
  `instances:`, not on the service, so the generic `requires_gpu` scan misses
  them — the same class of gap that previously let an invalid pin through.
- **Off by default.** Enabling both backends at once would put two servers on the
  one card that is already contended. Ollama stays the default until llama.cpp
  has run a lab window.
- The MoE VRAM figures are from published benchmarks, **not** measured on this
  hardware. The generated command has been verified against the real
  `llama-server` binary (every flag accepted), but the VRAM saving itself is not
  yet reproduced here. Reproducing it on the V100 box is the next step.

## Rejected

- **vLLM.** Better throughput and concurrency, and the standard choice for
  serving many users — but no MoE expert offload, which is the capability this
  change is for. Worth revisiting if the goal shifts from "share a card with
  image and voice services" to "serve 50 concurrent students".
- **Keeping Ollama and adding llama.cpp as an option permanently.** Two engines
  doubles the operator's surface for a PoC whose problem is too many knobs, not
  too few. Revisit if llama.cpp proves the residency behaviour and the format
  churn turns out not to matter.
- **Apple Silicon / unified memory as the answer to VRAM pressure.** Abandoned:
  ComfyUI on MPS cannot run the FP8 models, `channels_last` errors, and image
  generation runs at 20–90 s/image. Unified memory solves the LLM half and not
  the half that made this box distinctive. The target is now Linux + NVIDIA
  consumer hardware, i.e. a DIYer audience.