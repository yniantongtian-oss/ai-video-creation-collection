---
name: ai-video-editing
description: Convert existing video, screen recordings, talking-head footage, podcasts, or AI-generated clips into an executable automated editing plan, preferring the repository's Auto-Editor Skills. Use for silence or black-frame removal, sound/motion/transcript-based selection, transcript editing, speed changes, zoom, logos, picture-in-picture, volume handling, transcription, and exports to Premiere, DaVinci Resolve, Final Cut Pro, Shotcut, or Kdenlive. Preview edit decisions before rendering and never overwrite the source.
metadata:
  version: 1.0.0
  language: en-US
---

# AI Video Editing Skill

Convert "edit this for me" into **previewable, reversible, reproducible** Auto-Editor commands. This Skill interprets the request, selects an edit detector, generates safe commands, and verifies the output.

## Preflight

Run from the repository root:

```bash
python scripts/install_auto_editor.py
python scripts/check_video_editing_tools.py
```

Prefer the repository-local binary:

```text
tools/auto-editor/bin/auto-editor
tools/auto-editor/bin/auto-editor.exe
```

If the directory is already on `PATH`, `auto-editor` may be called directly.

Do not use `pip install auto-editor`; the upstream CLI is no longer distributed that way.

## Task routing

| Task | Skill |
|---|---|
| Remove silence, no-motion sections, black frames; manual trims; pacing | `../auto-editor/SKILL.md` |
| Speed, zoom, fades, volume, logos, PiP, animation | `../auto-editor-effects/SKILL.md` |
| Transcribe and keep/remove clips by keyword or dialogue | `../auto-editor-transcribe/SKILL.md` |
| Export Premiere, Resolve, Final Cut, Shotcut, Kdenlive, or clip sequences | `../auto-editor-export/SKILL.md` |

Complex tasks may combine Skills, but complete the rough cut before effects and export.

## Standard workflow

### 1. Protect source media

- Read source files only.
- Render to a new filename or `outputs/`.
- Never use the same input and output path.
- Record input path, output path, command, thresholds, and tool version.

### 2. Inspect media

```bash
auto-editor info input.mp4
```

Check duration, resolution, frame rate, audio tracks, and subtitle tracks. For multiple audio tracks, select one explicitly or use `stream=all`.

### 3. Preview first

```bash
auto-editor input.mp4 --preview
```

The first run of an automated edit should use `--preview`. Review expected removed duration, clip count, sentence boundaries, and low-volume speech.

### 4. Minimal rough cut

A reasonable starting point for talking-head or screen-recorded material:

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

After approval:

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  -o outputs/input_cut.mp4
```

Thresholds are starting points, not universal answers. Lower the audio threshold for quiet speakers and raise it for noisy recordings, then preview again.

### 5. Combine sound and motion

Keep sections with either sound or visible motion:

```bash
auto-editor input.mp4 \
  --edit "(or audio:0.03 motion:0.02)" \
  --margin 0.2s \
  --preview
```

Prefer motion detection for visual demos, gameplay, or silent footage. Prefer audio or transcript detection for talking-head, lecture, or podcast video.

### 6. Transcript-based editing

Generate subtitles:

```bash
auto-editor whisper input.mp4 /path/to/ggml-model.bin \
  --format srt \
  -o input.srt
```

Keep sections containing a word:

```bash
auto-editor input.mp4 --edit word:keyword --preview
```

Remove a filler word:

```bash
auto-editor input.mp4 --edit "(not word:um)" --preview
```

Transcript editing depends on ASR accuracy. Accent, dialect, proper nouns, overlapping speakers, and background music require manual spot-checking.

### 7. Effects and packaging

Speed up silence instead of removing it:

```bash
auto-editor input.mp4 -w:0 speed:6,volume:0.35 -o outputs/input_fast_silence.mp4
```

Add a logo:

```bash
auto-editor input.mp4 -w:1 add:./assets/logo.png -o outputs/input_logo.mp4
```

Add subtle dynamic zoom:

```bash
auto-editor input.mp4 -w:1 zoom:1..1.08:ease=inout -o outputs/input_zoom.mp4
```

Effects should support the information being communicated. Avoid gratuitous high-frequency rotation, aggressive zooming, or animation that reduces readability.

### 8. Export to professional editors

```bash
auto-editor input.mp4 --export premiere
auto-editor input.mp4 --export resolve
auto-editor input.mp4 --export final-cut-pro
auto-editor input.mp4 --export shotcut
auto-editor input.mp4 --export kdenlive
```

When an editor will continue manual work, prefer a project/timeline export or `clip-sequence` over only delivering a flattened render.

## Common recipes

### Tight talking-head rough cut

```bash
auto-editor talk.mp4 \
  --edit audio:-30dB \
  --margin 0.25s \
  --smooth 0.18s,0.12s \
  -anorm ebu \
  -o outputs/talk_cut.mp4
```

### Lecture recording with speech and on-screen actions

```bash
auto-editor lesson.mp4 \
  --edit "(or audio:0.025 motion:0.015)" \
  --margin 0.3s \
  -o outputs/lesson_cut.mp4
```

### Podcast with long pauses removed and speech slightly accelerated

```bash
auto-editor podcast.mp3 \
  -w:0 cut \
  -w:1 speed:1.08 \
  -anorm ebu \
  -o outputs/podcast_tight.m4a
```

### Rough cut, then DaVinci Resolve

```bash
auto-editor interview.mp4 \
  --edit audio:-28dB \
  --margin 0.3s \
  --export resolve \
  -o outputs/interview.fcpxml
```

## Acceptance criteria

- The source file is unchanged.
- Sentence starts and endings are not visibly clipped.
- Important silent visuals, title cards, pauses, or interaction sequences are preserved.
- Audio/video sync, duration, and frame rate meet delivery requirements.
- Subtitle text and timing are spot-checked.
- Exported projects open in the target editor.
- Commands, tool versions, and key thresholds are recorded.

## Fallbacks

- Speech removed accidentally: lower the audio threshold, increase `--margin`, or use transcript detection.
- Too much noise retained: raise the threshold, select the correct audio track, or denoise first.
- Too many tiny cuts: increase the minimum cut/keep duration in `--smooth`.
- Important silent visuals removed: combine motion detection or force-keep the required range.
- Automated effects are unsatisfactory: export a professional editing project and refine manually.

## Boundaries and licensing

- Upstream Skill text comes from `WyattBlue/auto-editor`, whose code and Skills use Unlicense/public-domain terms; see `THIRD_PARTY_NOTICES.md`.
- Official release binaries may contain components under separate licenses; review the relevant release and upstream documentation.
- Never describe automated editing as requiring no human review. Review subtitles, identity-sensitive material, commercial releases, and critical content.
