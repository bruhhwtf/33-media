# BANDKLAN CUTLAB

Local Windows desktop cutout editor: import → trim → click a subject → track/correct a SAM 2 mask → layer delayed cutouts → render preview → export MP4 with source audio.

Electron + React + TypeScript UI; independently testable Python/Pillow compositor and FFmpeg pipeline. A restrained Premiere-style layout with early-2000s red chrome and brushed-metal playback controls. No generative video or required cloud services.

**Simplified Windows installer:** the new release workflow bundles Python and FFmpeg. Its first-run wizard installs AI after an explicit download approval. No installer binary has been built/tested on Windows yet. See the final section of the Windows guide for build/status details.

**Source development setup:** [Windows setup and usage](docs/WINDOWS.md). [Timing, masks and architecture](docs/ARCHITECTURE.md). [Actual validation and limitations](docs/VALIDATION.md).

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1
powershell -ExecutionPolicy Bypass -File scripts/setup-model.ps1 -AcceptLargeDownload
powershell -ExecutionPolicy Bypass -File scripts/launch-windows.ps1
```

The app asks before downloading ~156 MB of official SAM 2.1 Tiny weights. Model dependency installation is a separate explicit several-GB step. The new installer configuration bundles Python and FFmpeg; PyTorch and weights download only through the first-run setup action. Real SAM tracking and Windows packaging are not yet validated in this Linux instance; generated-media FFmpeg tests and synthetic-mask compositor checks are reported separately.
