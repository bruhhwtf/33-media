# BANDKLAN CUTLAB — Windows 10/11 x64

This is a single-clip desktop editor. No service, account, paid API, login or cloud processing is required. It never generates replacement video content. SAM 2 predicts alpha masks; compositing always copies pixels from your footage.

## Install and run from source

1. Install **Node.js 24 LTS**, **Python 3.11 x64** (include the `py` launcher), **Git for Windows**, and **FFmpeg** with `ffprobe`. Use official sources: https://nodejs.org/, https://www.python.org/downloads/windows/, https://git-scm.com/downloads/win, https://ffmpeg.org/download.html. FFmpeg links Windows build providers. Add its `bin` directory to PATH. Keep their license notices. Verify `node --version`, `py -3.11 --version`, `git --version`, `ffmpeg -version`, `ffprobe -version` in a fresh terminal.
2. In PowerShell, from this repository: `powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1`. This installs pinned base Python and npm dependencies, builds the UI, and saves `CUTLAB_PYTHON` as a user environment variable. It does not install a model. Python lives under `%LOCALAPPDATA%\BANDKLAN-CUTLAB\python`.
3. For real tracking: `powershell -ExecutionPolicy Bypass -File scripts/setup-model.ps1 -AcceptLargeDownload`. This explicit step downloads **several GB** of PyTorch CUDA packages and installs pinned SAM 2 source. It does not download weights. Update your NVIDIA driver if CUDA is unavailable. A system CUDA toolkit is not needed because the optional SAM CUDA extension is disabled.
4. Run `powershell -ExecutionPolicy Bypass -File scripts/launch-windows.ps1`.
5. Open **Model setup**. Read the source/license/size and press **Download official Tiny weights** (~156 MB / 149 MiB). Progress and cancellation appear in that dialog. No silent weight download occurs. HTTPS certificate validation stays enabled; interrupted downloads are removed. A local SHA-256 receipt records the bytes received, not an independently published upstream checksum.

The model is **SAM 2.1 Hiera Tiny**, 38.9M parameters, **Apache 2.0**, official source https://github.com/facebookresearch/sam2 at commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`. Checkpoint: https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt. Upstream currently requires Python >=3.10, torch >=2.5.1, torchvision >=0.20.1 and strongly recommends **WSL for Windows**. This integration uses native Windows Python so paths and dialogs work together. Native SAM installation, GPU execution, the 512-pixel override's tracking quality, and the Windows installer have not been validated on Windows in this Linux environment. Do not assume upstream guarantees native support. Do not point `CUTLAB_PYTHON` at a WSL Python executable; that needs a path/process bridge which is outside this version.

### Your RTX 2070 / 16 GB PC

Diagnostics checks PyTorch CUDA availability, actual GPU name, VRAM, and `nvidia-smi` where available. No VRAM is assumed from your GPU model. RTX 2070 is Turing: inference uses float32, never assumes BF16, and does not compile the model. SAM input is 512 × 512 with reduced, aspect-preserving disk frames; video tensors and tracking state are offloaded to CPU. One subject, at most 10 seconds, timeline rate capped at 30 fps. Start with 5 seconds. All source-resolution export frames live on disk, not on the GPU. SAM loads the reduced clip into CPU RAM (roughly 0.9 GiB for 300 float32 512² RGB frames), and retains temporal state there; memory use is not constant. No real-time performance claim. CPU fallback is supported but can be very slow. Close other GPU-heavy apps; reduce trim length if memory runs out. Exporting 4K frames may require many GB of free disk space. There is no automatic cache eviction in v0.1.

## First edit

1. **Import MP4** (or drop a local MP4); metadata appears in the media bin. The original is retained. A ≤960 × 540 playback proxy is generated.
2. Set **Start / End** (maximum 10 seconds). Trimming clears clicks so they cannot silently refer to the wrong frames. Scrub and frame step.
3. **Select subject** opens an exact normalized frame. Click positive points on the person; shift-click or choose **Exclude** for negative points. **Mask Subject** runs SAM 2 across the trim. The overlay appears after tracking completes.
4. To correct, seek/frame step in mask mode, add clicks, then run **Mask Subject** again. All correction frames are supplied as conditioning frames before forward/backward propagation. No brush tool is implemented.
5. Adjust feather/expand, echoes, analog finish, or use CLEAN CUTOUT / GHOST TRAIL / DIRTY TAPE. Settings never invalidate segmentation unless source, trim or prompts change.
6. **Render Preview** renders the actual composite at ≤640 × 360. The stale badge appears whenever saved settings differ. **Export MP4** uses original-resolution frames, source aspect ratio, even dimensions, no upscaling, H.264 yuv420p and optional AAC audio. Choose a new filename; existing media and the source cannot be overwritten. Preview rendering is cached video playback, not real-time shader preview.
7. **Save project** stores a versioned JSON reference, prompts, trim, effects, cache reference, and output quality. **Open project** restores it. Missing source opens the Relink workflow. No video or weights are embedded. Move the same original, not a different edit, when relinking; prompts are normalized to its picture. A changed file identity automatically invalidates frame/mask caches.

## Packaging

The new Windows installer bundles Python and FFmpeg and offers AI setup inside the
app. See **Simplified installer (new)** below for the build workflow, included
components, and current validation limits. Source-development scripts above remain
available for developers; end users of a successful installer build do not need them.


## Troubleshooting

- **Cannot start Python**: run base setup, verify `CUTLAB_PYTHON` points to an existing executable, and restart Electron.
- **FFmpeg/ffprobe missing**: add the FFmpeg bin directory to PATH and restart. Model setup diagnostics shows both tools independently.
- **SAM/PyTorch missing**: run the explicit model install script using the same Python as Electron.
- **Weight download denied**: allow `dl.fbaipublicfiles.com` in your firewall/environment network settings. Git installation also needs github.com; Python packages need pypi.org, files.pythonhosted.org and download.pytorch.org. No verification bypass is provided.
- **CUDA false**: check the NVIDIA driver and the cu124 PyTorch wheel. The app falls back to CPU; it never labels that GPU inference.
- **Mask missing/stale**: track after adjusting trim/clicks. Effects alone reuse cached masks. Setting duplicates to zero permits editing/export without a model.
- **Cancelling**: cancellation is cooperative, checked between decoded/composited/tracked frames and during FFmpeg execution. Model loading or a single GPU inference can take time to return. Active render directories and unfinished weight downloads are removed; completed caches remain. Closing the window requests cancellation. In a forced process kill, partial cache files may remain and are rebuilt on the next run.
- **Clear disk cache**: with the app closed remove `%APPDATA%/bandklan-cutlab/cache` (Electron userData location may vary with application naming). This deletes cached frames, masks, previews and downloaded weights; it does not touch original media or project JSON. The worker uses the userData path shown by Electron, never a source-adjacent cache.

Tests: `npm run build`, `npm test` (Windows: `& $env:CUTLAB_PYTHON -m unittest discover -s tests -v`). See [VALIDATION.md](VALIDATION.md) for tested and untested capabilities.

## Simplified installer (new)

The Windows release build now bundles an isolated Python 3.11.9 interpreter, pip,
base dependencies, FFmpeg and ffprobe. End users do **not** need Node, Git, Python,
a compiler, PATH edits or terminal commands. Double-click the NSIS installer,
launch CUTLAB from its shortcut, and choose **Set up AI · approve downloads** in
the first-run wizard. Base editing works without the optional AI installation.

The wizard explicitly downloads several GB of PyTorch CUDA 12.4 packages and the
~156 MB official Tiny checkpoint. Allow at least 10 GB free disk space. It shows
phase progress for package installation and byte progress for weights, supports
Cancel and retry, and commits packages only after fresh-process imports succeed.
No account or paid API is involved. Inference remains local. Drivers still come
from NVIDIA; the wizard detects CUDA availability and reports CPU fallback.

Bundled files are copied once to the app's userData/runtime-v1 folder so AI packages
are never installed into Program Files. Interrupted staging is discarded. Valid
AI packages survive restarting the app and retrying a failed checkpoint download.
This overrides the earlier section saying Python/FFmpeg are separately installed:
that description applies only to the old source-only build. Model weights and
PyTorch remain explicit first-run downloads; neither is included in the installer.

### Producing the installer

The workflow `.github/workflows/windows-installer.yml` builds on Windows x64 and
uploads the installer as a GitHub Actions artifact. Run **Build Windows installer**
from the repository's Actions tab after this source is committed/pushed, or create
a version tag. It installs pinned npm packages, builds the embedded runtime and
pinned SAM wheel, tests Python and the actual Electron workflow, then builds NSIS.
This task has not pushed changes or triggered a remote build.

Local developer equivalent on Windows: use Python 3.11 and Node 24, run `npm ci`,
`python scripts/bundle-windows.py`, then `npm run dist:win`. The build bundles the
pure Python SAM wheel from the pinned official commit, avoiding Git/compiler
requirements for end users. FFmpeg binary distribution notices are retained under
runtime/licenses; see the pinned ffmpeg-static and ffprobe-static package source
and build references there. Bundled Python retains its license. Build downloads
use HTTPS validation; receipts record archive SHA-256 values. These receipts are
not independently published upstream signatures.

**Status:** wizard, runtime selection, staging and release workflow are implemented.
Linux build/tests pass; an actual Windows release build and real AI package/model
installation have not yet run. No downloadable installer is claimed until that
workflow succeeds. Installer signing is not configured; unsigned Windows releases
may display a SmartScreen warning.

### Store AI and cache on D: or another drive

Open **Model setup → Choose AI storage folder…** before installing AI. Select a
folder on the desired drive; CUTLAB creates a BANDKLAN-CUTLAB subfolder, checks
writability and at least 10 GB free space, and remembers it across restarts. Model
packages, weights, frame/mask/render caches, pip's download cache and worker
TEMP/TMP files use that drive. Only the small preference file, Electron profile
and the installed application remain in their normal locations on C:.

Changing locations preserves files at the old location; it does not move or delete
them. Reinstall AI in the new location if needed. Once the new installation works,
you may remove the old app-owned cache/runtime folders to reclaim space. Keep
external drives connected while editing. Original footage and project files are
never moved by this picker.
