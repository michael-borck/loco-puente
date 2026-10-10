# 0009 — Custom images are published to GHCR from a pinned commit

**Status:** Accepted (2026-10-08)

## Context

Six services cannot simply pull an upstream image:

- **swarmui, fooocus, comfyui, nodepad** — upstream ships a Dockerfile but no
  image, so Puente carries its own build context under `puente/dockerfiles/`.
- **voicebox** — upstream publishes no image *at all*, and the version Puente
  needs does not exist upstream either: `jamiepine/voicebox#889` ("Add opt-in
  idle model unloading to free VRAM") is **open**, and without it an idle
  instance pins ~5.6 GB of weights until the process restarts, which is most of
  a small card.
- **tutor-admin** — not an image problem at all. The container ran
  `pip install pymongo` in its entrypoint, so it needed outbound PyPI access to
  start, ran whatever version was published that day, and failed in a way that
  looked like a hung app. That is an air-gapped-host failure and an unpinned
  dependency in an account-administration surface, and an image fixes both.

Without a published image, the first `puente up voicebox` on any new machine
compiles torch + CUDA from source: 10–20 minutes with long silent stretches. That
is acceptable once on the machine where the image was built. It is not acceptable
as the *only* path, because it means every future host — and every institution
picking up LocoPuente — pays the compile, with no progress output and no obvious
indication that anything is wrong.

The obvious alternative, building locally on the target box and pushing from
there, was rejected: it fixes exactly one machine and leaves the problem intact
for the next one, while producing an artifact nobody can audit.

## Decision

1. **CI publishes all six images to GHCR.** `build-images.yml` already built
   four successfully; voicebox and tutor-admin join it. tutor-admin's image
   exists solely to pin `pymongo` — it carries no application code, since the
   app is one stdlib file copied into the bind mount on every `up`.

2. **The compose fragment carries both `image:` and `build:`.** Docker pulls the
   published image and only compiles if the pull fails. The fallback is retained
   deliberately — it is the escape hatch for an arm64 host, a not-yet-published
   tag, and an unreachable registry.

3. **Voicebox's `build_ref` is pinned to a commit SHA, and the workflow reads
   that SHA out of `puente.yml`.** The job rejects anything that is not a
   40-character hex SHA. A branch name would make the published image drift from
   what a local source build produces — the same config yielding different images
   on different days, which is precisely what a published artifact exists to
   prevent.

4. **Images stay `linux/amd64` only.** Every current target is x86. No
   `platforms:` key is set, and adding one is called out as wrong rather than
   merely unnecessary: these are CUDA services, CUDA does not exist on Apple
   silicon, so a naive multi-arch build would publish an arm64 image that cannot
   perform GPU work at all. The M3 Ultra in the Phase 2 roadmap will need its own
   image set, not a platform flag. `puente doctor`'s `image-arch` check reports the
   mismatch on an arm64 host and names the source-build fallback.

   > **Note, 2026-10-10:** the decision above stands — images remain `linux/amd64`
   > only — but one of its justifications is now moot. The M3 Ultra referenced here
   > is no longer part of the plan; the target audience is Linux + NVIDIA consumer
   > hardware (ADR0010). So amd64 is the target by definition rather than because
   > CUDA cannot run on Apple silicon. Nothing else in this ADR changes.

5. **The workflow smoke-tests the artifact it just pushed.** A build that
   succeeds but produces an image with the wrong torch variant, or without the
   fork's `idle_unload` module, is worse than a build failure — it surfaces later
   as a mysterious service problem. The job pulls the image back and asserts on
   its contents.

## Consequences

- A new machine pulls voicebox instead of compiling it, and tutor-admin starts
  with no outbound network access at all.
- `puente up voicebox` warns before any fallback compile rather than appearing to
  hang.
- tutor-admin's `pymongo` is pinned at build time. Bumping it is a Dockerfile
  edit plus a `puente up tutor_admin`.
- When #889 merges upstream, `build_ref` is dropped from `puente.yml` to track
  upstream, and the workflow is re-run. The smoke test's `idle_unload` assertion
  is removed at the same time, since the module would then be upstream's.
- **The images must be public in GHCR.** They are — verified by pulling the
  manifest with no credentials. Worth stating as a requirement rather than a fact
  though: the build authenticates with a `GITHUB_TOKEN` that can read private
  packages, so a private image looks fine to the machine that built it while
  every other host gets a 401 and falls through to a source build for every
  custom service — the exact outcome this ADR removes. Visibility is a package
  setting the workflow does not control, so it is an operational step to check on
  first publish of each new image.

## Alternatives considered

- **Local build on each target box, pushed manually.** Fixes one machine; leaves
  every other host with the compile. Rejected.
- **Publish voicebox without the fork**, tracking upstream main and losing idle
  unloading. Defeats the reason voicebox is preferred over upstream's own image
  on a shared-GPU box. Rejected until #889 merges.
- **Multi-arch (`linux/amd64,linux/arm64`) from the start.** Correct in shape,
  wrong in substance for CUDA services — see consequence 4. Deferred to the M3
  Ultra phase, where it needs different base images anyway. tutor-admin *is*
  published for both, because it has no CUDA dependency and the extra manifest
  costs a couple of seconds to build.