# Validation record

Validated in the Linux cloud checkout, with Node 24.19.0, Python 3.12.14, system FFmpeg/ffprobe, pinned npm packages and base Python dependencies. Windows setup targets Python 3.11. No user footage was attached; the supplied pictures were UI references only.

## Passed — actual running application

- `bash scripts/setup-cloud.sh`: fresh `.venv`, exact base Python versions, `npm ci`, TypeScript check, production Vite build and backend tests.
- `bash scripts/launch-cloud.sh --test`: creates its own isolated Xorg dummy display and runs the **actual Electron binary**, scoped preload/IPC, Python worker and FFmpeg. It stops its own display afterward. No browser-only backend simulation.
- Desktop smoke: generated 320×240 MP4 with audio, path containing spaces, import/proxy playback (`readyState >= 2`), 0.25–1.75s trim, zero-duplicate rendered preview playback, real H.264/AAC export, duration within one frame, project save/open restores trim/effects, exact frame canvas, stored positive click, actionable missing-SAM error, missing-source project and successful relink. No renderer JavaScript errors were observed. File dialogs are automated by returning test paths in Electron's main process; media/backend operations are real.
- Brushed-metal/red-chrome UI visually inspected at 1440×940. Three-column editing layout, timeline, inspector tabs, preset selection, compact controls, progress/cancellation and model information dialog are implemented.
- `git diff --check` and Node syntax checks pass.

## Passed — 17 Python tests, no skips

Generated FFmpeg videos exercise import/export with real decoding and encoding, trim duration within one output frame, an audio frequency transition occurring at its correctly trimmed timestamp, an audio stream with delayed onset, silent source/export, VFR-to-CFR PTS spacing, non-square-pixel display aspect without upscaling, source-overwrite prevention, cancellation of an active FFmpeg process, cancellation cleanup of composition outputs, and project JSON round-trip.

**Synthetic mask fixtures only** exercise image/mask delayed-index pairing, no negative-index wraparound, current-subject top ordering, identity with zero duplicates/all analog effects disabled, deterministic timestamp grain, nonwrapping RGB offsets, same-size preview/export pixel equivalence, lower-resolution preview/full-resolution agreement (mean RGB error <3/255), mask frame numbering/alignment, and cached-mask reuse after effect changes. The cache-hit test calls the real mask operation with an already populated fixture cache while SAM is absent; changing effects must not invoke segmentation. Prompts change the mask key.

## Real segmentation — integrated, not executed

Official SAM 2 README, license, video predictor, builder, setup flags, base model and Tiny config were fetched and inspected at pinned commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`. Real calls are `build_sam2_video_predictor`, `init_state`, `add_new_points_or_box` and bidirectional `propagate_in_video`, with CPU offloading, one object, float32 and a reduced `image_size` override. Correction frames edit an established track before final repropagation. No fallback creates synthetic production masks.

This instance has **no PyTorch, no installed SAM package, no weights, and no detected CUDA device**. The official weight URL returned a network-policy 403. `dl.fbaipublicfiles.com` was added to the environment configuration draft; saving the draft does not apply/publish it. Real checkpoint loading, 512-pixel inference compatibility, tracked accuracy, holes/limbs, corrections, GPU/VRAM usage and speed on an RTX 2070 remain **unverified**. The model dependency installer is supplied for Windows and has not been executed in this Linux task. Fixture results are not evidence of AI quality.

## Remaining limitations

- Native Windows execution, PowerShell install scripts and an NSIS installer build are untested. Packaging configuration is supplied; no installer or signed executable is claimed. Upstream SAM 2 strongly recommends WSL on Windows; native installation may need troubleshooting.
- No real-footage end-to-end check was possible without footage and a working model installation. No performance or real-time claim.
- Video/cutout RGB comes from original decoded frames. JPEG inference copies affect mask estimation only. Tiny/reduced inference may miss fine lettering-adjacent boundaries or separated limbs; it cannot promise accurate rotoscoping on all footage.
- Cancel is cooperative; a current model load/inference may finish before the next check. Hard process termination can leave partial caches, which a later run rebuilds. There is no cache-management UI.
- Mask overlay shows the cached raw prediction. Feather/expand and all effects are reflected by rebuilding the actual rendered preview.
- Preview uses the same composition at a smaller resolution; resampling, quantized edge widths and lossy H.264 encoding can create small pixel differences. Timing and source/mask frame identities agree.
- Source monitor uses a lightweight proxy; exact frame stepping switches to normalized segment inspection. This is a short single-subject editor, not a multi-track NLE.
- The npm audit after upgrading Electron/Vite/builder reported **0 high/critical** issues and 15 moderate transitive packaging/development advisories. Production React dependencies have no reported advisories in that audit. No signature/TLS/checksum verification was disabled to make installation pass.

## Re-run

```
npm run build
.venv/bin/python -m unittest discover -s tests -v
bash scripts/launch-cloud.sh --test
```

On Windows, run the Python tests using `$env:CUTLAB_PYTHON`, then `npm run test:desktop` from a built checkout. Desktop test expects SAM to be absent for its missing-model assertion; it deliberately does not run segmentation. To validate real segmentation, install dependencies/weights explicitly, import representative footage, seed/correct a real person, render/export, and compare mask alignment/audio at several known timestamps. That manual/model check remains outstanding.

## Installer/wizard update

The NSIS configuration now includes portable Python and FFmpeg/ffprobe built on
Windows. An explicit first-run action installs staged AI dependencies from pinned
packages and a vendored SAM wheel, validates imports, then downloads weights. Base
runtime and package-path selection, reuse, missing-runtime cleanup and setup
command guards have local tests. React startup checks status and opens the wizard
only when bundled runtime setup is available and AI is missing. Linux developer
launches continue to use .venv.

The Windows workflow has not been run, and no installer artifact was produced in
this Linux task. End-user Python/FFmpeg installation is no longer necessary for a
successful new installer build, superseding the old packaging limitation above.
Windows embedded-Python pip compatibility, native SAM wheel installation, download
cancellation on Windows and real-model execution still require Windows validation.
