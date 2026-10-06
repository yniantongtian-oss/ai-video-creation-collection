# AI-Assisted Video Editing: Setup and Usage

This repository includes an executable video-editing workflow built around **Auto-Editor**. It is suitable for AI-generated clips, talking-head footage, course recordings, interviews, podcasts, and gameplay. It supports silence removal, motion-based selection, black-frame handling, transcription, transcript-based editing, speed changes, overlays, and export to professional NLEs for manual refinement.

## Included Skills

```text
skills/ai-video-editing/        Unified entry point and task router
skills/auto-editor/             Silence, motion, black frames, manual ranges, basic rendering
skills/auto-editor-effects/     Speed, volume, zoom, overlays, picture-in-picture, animation
skills/auto-editor-transcribe/  Whisper/Parakeet transcription and transcript-based editing
skills/auto-editor-export/      Premiere, Resolve, Final Cut, Shotcut, Kdenlive export
```

Tools that support Agent Skills can load these directories directly. For general editing requests, start with `skills/ai-video-editing`; it routes work to the appropriate upstream Skill.

## 1. Download the official Auto-Editor binary

The installer uses only the Python standard library and selects an official GitHub Release binary for the current operating system and CPU architecture:

```bash
python scripts/install_auto_editor.py
```

Default installation path:

```text
tools/auto-editor/bin/auto-editor
tools/auto-editor/bin/auto-editor.exe
```

Preview the download plan without downloading:

```bash
python scripts/install_auto_editor.py --dry-run
```

Install a specific upstream release:

```bash
python scripts/install_auto_editor.py --version 30.3.0
```

Replace an existing local binary:

```bash
python scripts/install_auto_editor.py --force
```

After download, the script runs `--help` as a startup check and records source, version, asset name, and download URL in `tools/auto-editor/install.json`. The binary and local installation record are Git-ignored.

> Auto-Editor CLI is no longer distributed through pip. Do not add `pip install auto-editor` to new installation flows. Use official release binaries, Homebrew, or a source build as recommended upstream.

## 2. Check the environment

```bash
python scripts/check_video_editing_tools.py
```

Machine-readable output:

```bash
python scripts/check_video_editing_tools.py --json
```

`auto-editor` is required. System-level `ffmpeg` and `ffprobe` are optional helpers; official Auto-Editor binaries already include the media components they need.

## 3. Run the repository-local binary

### Windows PowerShell

```powershell
$AE = ".\tools\auto-editor\bin\auto-editor.exe"
& $AE --help
```

### macOS / Linux

```bash
AE=./tools/auto-editor/bin/auto-editor
"$AE" --help
```

You may add the directory to `PATH` and run `auto-editor` directly. The installer does not modify the system `PATH`.

## 4. First automated rough cut

Inspect the source:

```bash
auto-editor info input.mp4
```

Always preview the first edit decision:

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

After verifying that sentence boundaries and intentional pauses are preserved, render a new file:

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  -o outputs/input_cut.mp4
```

The repository ignores `outputs/` and common video formats to reduce the chance of committing large media files.

## 5. Common patterns

### Remove silence

```bash
auto-editor talk.mp4 --edit audio:-30dB --margin 0.25s --preview
```

### Keep sections with sound or motion

```bash
auto-editor demo.mp4 --edit "(or audio:0.03 motion:0.02)" --preview
```

### Speed up silence instead of deleting it

```bash
auto-editor lesson.mp4 -w:0 speed:6,volume:0.35 -o outputs/lesson_fast.mp4
```

### Add a logo

```bash
auto-editor input.mp4 -w:1 add:./assets/logo.png -o outputs/input_logo.mp4
```

### Add a subtle dynamic zoom

```bash
auto-editor input.mp4 -w:1 zoom:1..1.08:ease=inout -o outputs/input_zoom.mp4
```

### Export to DaVinci Resolve

```bash
auto-editor interview.mp4 --edit audio:-28dB --margin 0.3s --export resolve
```

Other export targets include:

```text
premiere
resolve
final-cut-pro
shotcut
kdenlive
clip-sequence
v1 / v2 / v3
```

## 6. Transcription and transcript-based editing

Auto-Editor can use Whisper, Parakeet, or supported Apple Speech backends. Model weights can be large and may use different licenses, so this repository does not host them.

Generate SRT subtitles:

```bash
auto-editor whisper input.mp4 /path/to/ggml-model.bin \
  --format srt \
  -o input.srt
```

Keep sections containing a word:

```bash
auto-editor input.mp4 --edit word:keyword --preview
```

Exclude sections containing a filler word:

```bash
auto-editor input.mp4 --edit "(not word:um)" --preview
```

Accent, dialect, proper nouns, overlapping speakers, and background music can reduce transcription accuracy. Always spot-check subtitles and edit points before relying on transcript-based cuts.

## 7. Let an AI agent use the workflow

Example request:

```text
Load skills/ai-video-editing. Analyze input.mp4 and preview a silence-removal edit.
Do not overwrite the source file. Render the approved result to outputs/input_cut.mp4
and also export a DaVinci Resolve project.
```

The agent should follow this order:

```text
Inspect source → choose detector → preview edit decisions → review cut points
→ render a new file → verify output → export an NLE project if requested
```

Never claim the video has been edited unless the workflow actually ran and produced output.

## 8. Update Auto-Editor

Preview the latest downloadable version:

```bash
python scripts/install_auto_editor.py --dry-run
```

Update and validate:

```bash
python scripts/install_auto_editor.py --force
python scripts/check_video_editing_tools.py
```

After upgrading, validate common commands on a short clip. Auto-Editor arguments, export formats, and component behavior can change upstream.

## 9. Licensing and safety

- The four imported upstream Skills come from `WyattBlue/auto-editor`, which declares them under Unlicense/public-domain terms.
- Official release binaries may bundle media components under different licenses; refer to the corresponding release and upstream files.
- Detailed provenance and versions are recorded in `THIRD_PARTY_NOTICES.md`.
- Do not overwrite source media, publish outputs automatically, or make unverified accuracy claims about subtitles or edit points.
