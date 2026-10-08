# AI Video Creation Collection

An executable resource collection for **long-form video, web research, open media, AI scripting, voice-over and subtitles, automated editing, video generation, and Agent Skills**.

This repository organizes research, asset discovery, script writing, storyboarding, narration, subtitles, chapter rendering, and final assembly into reproducible workflows that can resume from checkpoints. Core integrations prefer official or original-author repositories. Always verify licenses for models, APIs, media, and binaries before release.

## Core capabilities

- Produce **60–360 minute** documentaries, explainers, courses, and feature videos.
- Batch-ingest PDF, DOCX, PPTX, web pages, subtitles, spreadsheets, and local research files.
- Preserve SHA-256 hashes, page numbers, slide references, and source markers.
- Summarize source by source, build chapter outlines, retrieve chapter context, and draft each chapter.
- Plan hundreds of visual shots for hour-plus productions.
- Search Wikimedia Commons, Openverse, Pexels, and Pixabay.
- Record creator, source page, license, attribution, and file hash for media assets.
- Treat automatically downloaded assets as candidates until they pass review.
- Generate chapter voice-over and SRT subtitles with Edge TTS.
- Cache shots, render chapters, assemble the final video, and write chapter metadata with FFmpeg.
- Generate short videos with MoneyPrinterTurbo.
- Create commentary and automated edits from existing footage with NarratoAI.
- Create subtitles, translations, and multilingual dubbing with VideoLingo.
- Use Auto-Editor for silence, motion, transcript-based rough cuts, and professional timeline export.
- Use Wan2.2 ComfyUI workflows to generate missing AI shots.

## 90-minute production quick start

### 1. Install

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection

python scripts/install_web_media_stack.py --profile full
python scripts/install_longform_stack.py
python scripts/install_auto_editor.py
```

Preview the installation plan only:

```bash
python scripts/install_longform_stack.py --dry-run
```

Edit the local configuration:

```text
tools/longform/.env
```

At minimum, set:

```text
LONGFORM_LLM_BASE_URL=https://your-service.example/v1
LONGFORM_LLM_API_KEY=your-key
LONGFORM_LLM_MODEL=your-model
```

### 2. Create a project

```bash
python scripts/scaffold_longform_project.py \
  --name "space-solar-power-documentary" \
  --topic "History, principles, engineering approaches, debates, and future of space-based solar power" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --audience "General viewers interested in technology"
```

The default plan is approximately:

```text
13 chapters
about 23,400 narration characters
about 540 visual segments
```

### 3. Add research material

Place PDF, DOCX, PPTX, TXT, Markdown, extracted web text, and subtitle files in:

```text
projects/space-solar-power-documentary/research/inbox/
```

### 4. Research, draft, and plan shots

```bash
python scripts/run_longform_project.py \
  --project "projects/space-solar-power-documentary" \
  research
```

### 5. Search for candidate assets

```bash
python scripts/run_longform_project.py \
  --project "projects/space-solar-power-documentary" \
  assets \
  --execute-search \
  --download-first 1
```

### 6. Review assets

List candidates:

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/space-solar-power-documentary/manifests/assets.jsonl" \
  --candidates
```

Approve an asset:

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/space-solar-power-documentary/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "Verified content, source page, license, and attribution requirements"
```

### 7. Narrate, render, and assemble

```bash
python scripts/run_longform_project.py \
  --project "projects/space-solar-power-documentary" \
  produce
```

If assets have not been reviewed, the pipeline stops with:

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

This is an intentional copyright and relevance review gate, not a failure.

### 8. Final output

```text
outputs/final/<project-name>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
```

Full guide: [`docs/LONGFORM_VIDEO_PRODUCTION.md`](docs/LONGFORM_VIDEO_PRODUCTION.md)

## Why long-form production uses a chapter pipeline

Long-form video should not send tens of thousands of words and hundreds of assets to one model or renderer in a single pass. This repository uses:

```text
Research ingestion
→ Per-source summaries
→ Full-video outline
→ Per-chapter retrieval
→ Per-chapter drafting
→ Per-chapter shot planning
→ Asset review
→ Per-chapter narration
→ Per-chapter rendering
→ Final assembly
```

If one chapter fails, rerun only that chapter:

```bash
python scripts/longform_pipeline.py \
  --project "projects/<name>" \
  write \
  --chapter 4 \
  --force

python scripts/render_longform_narration.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force

python scripts/render_longform_chapters.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force
```

Check status:

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  status
```

## Main long-form Skill

```text
skills/longform-documentary-producer
```

It handles:

1. Choosing an appropriate long-form specification and chapter count.
2. Building a research corpus.
3. Per-source summarization and fact checking.
4. Generating chapter outlines and long-form scripts.
5. Planning hundreds of shots.
6. Finding and reviewing openly licensed media.
7. Chapter narration, subtitles, and rendering.
8. Final assembly and chapter timestamps.
9. Resuming from checkpoints after a failure at any stage.

## Web research and short-form video

Primary entry point:

```text
skills/web-media-producer
```

Installation profiles:

| Profile | Includes | Best for |
|---|---|---|
| `core` | yt-dlp, gallery-dl, Trafilatura | Web research and media archiving |
| `creator` | core + MoneyPrinterTurbo | Topic-to-short-video workflows |
| `full` | creator + NarratoAI + VideoLingo | Existing-video analysis, commentary, and multilingual dubbing |

```bash
python scripts/install_web_media_stack.py --profile core
python scripts/install_web_media_stack.py --profile creator
python scripts/install_web_media_stack.py --profile full
```

Full guides:

- [`docs/WEB_MEDIA_PRODUCTION.md`](docs/WEB_MEDIA_PRODUCTION.md)
- [`docs/WEB_MEDIA_APP_SETUP.md`](docs/WEB_MEDIA_APP_SETUP.md)

## AI-assisted editing

```text
skills/ai-video-editing
skills/auto-editor
skills/auto-editor-effects
skills/auto-editor-transcribe
skills/auto-editor-export
```

Install:

```bash
python scripts/install_auto_editor.py
python scripts/check_video_editing_tools.py
```

Always preview the first cut:

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

Full guide: [`docs/VIDEO_EDITING_SETUP.md`](docs/VIDEO_EDITING_SETUP.md)

## ComfyUI video-generation workflows

| Workflow | File | Default target |
|---|---|---|
| Wan2.2 text-to-video | `workflows/wan22_t2v_4step.json` | about 5 seconds |
| Wan2.2 image-to-video | `workflows/wan22_i2v_4step.json` | about 5 seconds |
| Three-shot continuous video | `workflows/wan22_long_video_3shot.json.gz` | about 15 seconds |

Materialize compressed workflows:

```bash
python scripts/materialize_workflows.py
```

Preview model downloads before changing a ComfyUI installation:

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

## Skills

```text
skills/longform-documentary-producer   60–360 minute long-form production
skills/web-media-producer              web research and media-to-video production
skills/moneyprinterturbo-video         topic-to-short-video production
skills/ai-video-creation               AI video model and workflow planning
skills/ai-video-editing                automated editing of existing footage
skills/auto-editor                     core automated editing
skills/auto-editor-effects             video effects
skills/auto-editor-transcribe          transcription and transcript-based editing
skills/auto-editor-export              professional timeline export
```

## Key scripts

```text
scripts/install_longform_stack.py        install the long-form runtime
scripts/scaffold_longform_project.py     create a long-form project
scripts/ingest_longform_corpus.py        extract and index research material
scripts/longform_pipeline.py             summaries, outline, script, and shot plan
scripts/build_longform_asset_plan.py     batch asset-search planning
scripts/media_asset_manifest.py          media licensing and approval
scripts/render_longform_narration.py     per-chapter narration and subtitles
scripts/build_longform_timeline.py       map assets to shots
scripts/render_longform_chapters.py      per-chapter rendering
scripts/assemble_longform_video.py       final assembly and chapter metadata
scripts/longform_preflight.py            environment, disk, and quality preflight
scripts/run_longform_project.py          top-level controller
```

## Validate the repository

```bash
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python -m json.tool tools/web-media-stack.lock.json >/dev/null
python -m json.tool tools/longform-stack.lock.json >/dev/null
python -m py_compile scripts/*.py skills/moneyprinterturbo-video/mpt_agent.py
```

## Maintenance principles

- **Split long-form work into chapters:** do not rely on one oversized request or a single rendering pass.
- **Keep sources traceable:** preserve source markers and write `NEEDS_SOURCE` when evidence is insufficient.
- **Review assets before use:** automatic downloads are candidates, never automatically approved final media.
- **Prefer clear licensing:** prioritize public-domain, Creative Commons, platform-licensed, and user-owned material.
- **Treat source media as read-only:** write results into project directories instead of overwriting originals.
- **Resume from checkpoints:** skip already generated summaries, narration clips, shot caches, and rendered chapters by default.
- **Never commit secrets:** real API keys, model files, source video, audio, and rendered outputs are Git-ignored.
- **Do not fake completion:** never claim that a video was generated unless the MP4 actually exists.
- **Recheck commercial terms:** this repository's MIT license does not override third-party software, model, voice, media, or codec terms.

## Third-party licenses

- Third-party sources and licenses: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- Video project catalog: [`catalog/projects.json`](catalog/projects.json)
- Long-form tool catalog: [`catalog/longform-tools.json`](catalog/longform-tools.json)
- Documentation index: [`docs/README.md`](docs/README.md)

## Disclaimer

This repository does not grant rights to third-party media, models, voices, fonts, music, or commercial audiovisual works, and it is not a substitute for legal review. Automated summaries, long-form scripts, subtitles, shot matching, license metadata, and final outputs require human review. Do not use this repository to bypass authentication, paywalls, CAPTCHAs, regional restrictions, robots rules, platform security controls, or DRM.
