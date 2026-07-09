# GPU swap: 2060 Super → 3090 (staged, not applied)

Replace the GPU 0 card (RTX 2060 Super, 8 GB, Turing) with an RTX 3090 (24 GB, Ampere),
keeping a 2060 Super in the second slot.

**Nothing in `puente.yml` needs to change** *if* the 3090 lands on index 0 — which it
will, provided you put it in the lower-numbered PCIe slot. Verify that before assuming.

## Why

GPU 0 currently carries ComfyUI, SwarmUI **and** Ollama on 8 GB. Every constraint we hit
is a VRAM wall, not a throughput wall:

| Workload | Today | On 24 GB |
|---|---|---|
| LatentSync (best lip-sync) | rejected — needs 20 GB | works |
| Wav2Lip, LivePortrait | hand-hardened to fit 8 GB | un-harden |
| `qwen3.5:27b`, `gemma4:26b` | deleted, 17–18 GB | usable |
| SDXL + LoRA + ControlNet | tight | headroom |
| ComfyUI vs Ollama | contend for one card | coexist |

Prefer the 3090 over the 4090: same 24 GB, and the bottleneck is capacity, not speed.
The Ryzen 5 2600 (2018) would also throttle a 4090 on anything not purely GPU-bound.

## Before you swap

- **PSU headroom.** 3090 is 350 W + 2060 Super 184 W = ~534 W of GPU alone, plus CPU.
- **Physical clearance.** The 3090 is a 2.5–3 slot card; check it does not foul slot 2.
- **Cables.** 3090 needs 2× 8-pin (or 3×, board-dependent).

## The card ordering trap

`nvidia-smi` numbers by **PCI bus order** (`06:00.0` → 0, `07:00.0` → 1). Docker's
`device_ids` uses that same ordering, so `gpu: 0` in `puente.yml` follows the slot.

But **CUDA defaults to `CUDA_DEVICE_ORDER=FASTEST_FIRST`**, so code *inside* a container
may renumber the 3090 as its device 0 even if it sits in the second slot. With two
identical 2060s this never mattered; with mixed cards it does.

Two rules keep this sane:

1. Put the **3090 in the lower-numbered slot** (currently `06:00.0`). Then PCI order and
   fastest-first agree, and nothing is ambiguous.
2. Where it matters, pin explicitly rather than relying on either default:
   `CUDA_DEVICE_ORDER=PCI_BUS_ID`.

## After the swap — verify before trusting

```bash
# 1. Confirm the 3090 is index 0 and on the lower bus id
nvidia-smi --query-gpu=index,pci.bus_id,name,memory.total --format=csv

# 2. Confirm containers see the card they expect
docker exec puente-comfyui nvidia-smi --query-gpu=name --format=csv,noheader   # 3090
docker exec puente-voicebox nvidia-smi --query-gpu=name --format=csv,noheader  # 2060
```

If the 3090 is **not** index 0, either move it to the other slot, or swap the `gpu:`
values below.

## puente.yml — no change needed (3090 in slot 0)

Current assignments already put everything heavy on GPU 0:

```yaml
comfyui:   { gpu: 0 }   # -> 3090 (24 GB)
swarmui:   { gpu: 0 }   # -> 3090
voicebox:  { gpu: 1 }   # -> 2060 Super (8 GB), lazy, ~4-5 GB when generating
```

Ollama is a **host systemd service, not puente-managed**. It is pinned in
`/etc/systemd/system/ollama.service` via `CUDA_VISIBLE_DEVICES=0`, which also follows
PCI order. No change needed, but note puente cannot manage it.

## Optional: exploit the 24 GB

**Park the everyday model in VRAM.** Ollama unloads after `OLLAMA_KEEP_ALIVE` (default
5 min), so occasional use pays a reload each time. With headroom you can keep
`qwen3.5:9b` (6.6 GB) resident:

```
# /etc/systemd/system/ollama.service
Environment="OLLAMA_KEEP_ALIVE=-1"
```

Then `sudo systemctl daemon-reload && sudo systemctl restart ollama`.

**Restore the big models** (they were deleted because they spilled on 8 GB):

```bash
ollama pull qwen3.5:27b     # 17.4 GB
ollama pull gemma4:26b      # 18.0 GB
```

**Un-harden the video pipelines.** Wav2Lip and LivePortrait were squeezed to fit 8 GB;
LatentSync (20 GB) was rejected outright. All three can be revisited.

## What multiple co-resident models does and does not buy

Nothing partitions VRAM — Docker's `device_ids` grants *visibility*, not exclusivity.
Two models on one card simply both allocate until it fills, then someone OOMs.

- **Buys:** keeping several things *warm*. A parked `qwen3.5:9b` (6.6 GB) plus a resident
  SDXL (~8 GB) fits in 24 GB with ~9 GB spare. Neither evicts the other, so you stop
  paying the load tax at the start of every interaction. That is a **latency** win.
- **Does not buy:** speed. Concurrent models time-slice the same SMs. Two busy models
  each get roughly half the GPU. Concurrency buys *availability*, not throughput.
- **Watch out:** LatentSync alone wants 20 GB. It cannot coexist with a parked LLM —
  big video jobs need the card to themselves. Budget ~3 GB for KV cache and fragmentation;
  do not plan to fill 24 GB exactly.

## Note on ts_server

The 3090 is Ampere (sm_86), which satisfies ts_server's documented
"Ampere, ADA or Hopper" requirement — unlike the Turing 2060s. Worth a single test:

```bash
cd eval/ts_server && LD_LIBRARY_PATH=. ./ts_test --cuda -m models/gpt2_117M.bin g "hi"
```

If it **works**, the only remaining gaps are Qwen3.5 and SDXL — both software, both
Bellard's to answer, which is exactly what the draft email asks.

If it **still fails**, that is now a genuine bug report (Ampere card, CUDA 13.2 driver,
docs ask for CUDA 11.x/12.x) rather than a complaint about unsupported hardware.

Either way this does not change the verdict: ts_server cannot do SDXL, so it is not
replacing the ComfyUI/SwarmUI stack.
