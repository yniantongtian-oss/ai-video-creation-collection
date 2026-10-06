---
name: longform-documentary-producer
description: Build 60–360 minute documentaries, explainers, courses, historical narratives, investigations, and other long-form videos with a resumable chapter-based workflow. Ingest PDF, DOCX, PPTX, web documents, subtitles, and local research; build a searchable corpus; summarize sources; create a multi-chapter outline; draft and source-check each chapter; plan hundreds of shots; review media rights; narrate, subtitle, render, and assemble chapters. Preserve factual provenance and asset licensing. Never try to generate or render an entire long-form production in one pass.
metadata:
  version: 1.0.0
  language: en-US
---

# Long-Form Documentary Producer

Use a chapter-based pipeline for 60–360 minute productions:

```text
Project specification
→ research ingestion
→ per-source summaries
→ program outline
→ per-chapter retrieval and writing
→ per-chapter shot planning
→ open-media search
→ relevance and rights review
→ per-chapter narration and subtitles
→ per-chapter timeline and render
→ final assembly, chapter metadata, and quality report
```

Do not turn a short-video generator into a 60-minute job, send all research in one model request, or render the entire program as one indivisible task.

## Default design

When the user asks for "about an hour or more" without detailed specifications, start with:

- 90 minutes;
- 16:9, 1920×1080, 30 fps;
- about 13 chapters of roughly seven minutes;
- one major visual change about every 10 seconds;
- H.264 video and AAC audio;
- approximately 8 Mbps video bitrate;
- external SRT plus an optional subtitle track in the MP4;
- every automatically downloaded asset stored as a candidate with `selected=false`;
- independent chapter narration and rendering so failed chapters can resume separately.

Explicit user requirements for duration, aspect ratio, language, style, platform, and audience take precedence.

## Install

From the repository root:

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/install_longform_stack.py
python scripts/install_auto_editor.py
```

Preview the long-form installation:

```bash
python scripts/install_longform_stack.py --dry-run
```

Configuration lives in:

```text
tools/longform/.env
```

At minimum:

```text
LONGFORM_LLM_BASE_URL=https://your-service.example/v1
LONGFORM_LLM_API_KEY=your-key
LONGFORM_LLM_MODEL=your-model
```

Never print, commit, or repeat secrets.

## Create a project

```bash
python scripts/scaffold_longform_project.py \
  --name "project-name" \
  --topic "video topic" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --language en-US \
  --audience "General audience" \
  --style "Documentary explainer with high information density and natural narration"
```

Keep all research, media, intermediate outputs, and rendered files inside the project directory.

## Ingest research

Place research in:

```text
projects/<project-name>/research/inbox/
```

Supported inputs include PDF, DOCX, PPTX, TXT, Markdown, HTML, CSV/TSV/JSON, SRT/VTT, and extracted web documents.

Build the corpus:

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<project-name>"
```

Additional inputs can be supplied with repeated `--input` arguments.

The ingester should preserve file hashes and page/slide locators, extract text, create overlapping chunks, write JSONL, build the SQLite search index, and skip duplicate material. Scanned documents with no text layer require OCR; never pretend an empty extraction was successfully read.

## Research, outline, scripts, and shots

Run:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  research
```

Expected order:

```text
Per-source summaries
→ full outline
→ per-chapter retrieval
→ per-chapter script
→ per-chapter shot plan
```

Each chapter should preserve `[S:source_id#locator]` references in the editorial script and provide narration without spoken source markers. Use `NEEDS_SOURCE` when evidence is insufficient.

Rerun only chapter four when needed:

```bash
python scripts/longform_pipeline.py \
  --project "projects/<project-name>" \
  write \
  --chapter 4 \
  --force
```

## Media strategy

Do not perform a separate web search for every shot. Deduplicate shot needs into a smaller set of chapter-level search groups.

Search candidates with:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  assets \
  --execute-search \
  --download-first 1
```

Prefer, in order:

1. clearly licensed public-domain or Creative Commons material;
2. Openverse results with verifiable licenses;
3. provider-licensed B-roll from services such as Pexels or Pixabay;
4. institutional, archival, museum, academic, or public-sector material where reuse rights are clear;
5. user-owned media;
6. newly generated concept visuals when appropriate;
7. original maps, timelines, diagrams, and charts.

Do not fill a long video with unknown-source film, music, image-library, or social-media material.

## Review and approve assets

List candidates:

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --candidates
```

Review relevance, quality, provenance, license, attribution, privacy, likeness, trademark, minors, and sensitive-content risks.

Approve one item:

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "Verified relevance, source page, license, and attribution requirements"
```

Approval must revalidate file integrity, provenance, licensing, attribution, and permission notes.

## Narration, timeline, and rendering

After rights review:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  produce
```

This should perform:

```text
Rights/resource preflight
→ segmented chapter narration
→ chapter subtitle assembly
→ approved-media matching
→ per-shot cache
→ chapter rendering
→ final assembly
→ full subtitles and chapter timestamps
```

If approved media is insufficient, stop with:

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

Do not bypass this gate.

Individual stages can be rerun with the dedicated narration, timeline, chapter-render, and assembly scripts. After rerendering a chapter, run final assembly again.

## Existing video analysis

When users supply long videos, interviews, courses, documentaries, or large footage libraries:

1. obtain only lawful, authorized inputs;
2. transcribe with an appropriate tool such as VideoLingo, NarratoAI, or Auto-Editor;
3. sample frames at sensible intervals and scene changes;
4. analyze sampled frames rather than claiming to have visually inspected hours of footage in one pass;
5. record subtitles, timecodes, people, locations, shot type, and topic tags in the project;
6. feed that structured material into chapter retrieval and media matching.

Do not claim all footage was reviewed unless the required transcription/frame-analysis steps actually ran.

## Preflight and checkpoints

Run:

```bash
python scripts/longform_preflight.py --project "projects/<project-name>" --stage setup
python scripts/longform_preflight.py --project "projects/<project-name>" --stage render
python scripts/longform_preflight.py --project "projects/<project-name>" --stage final
```

Inspect runtime configuration, disk space, source corpus, summaries, outline, script completeness, shot count, approved assets, licenses, placeholders, narration duration, rendered chapters, and final assembly readiness.

Check state with:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  status
```

Existing valid summaries, scripts, narration segments, shot caches, and chapter renders should be reused. Use `--force` only when an artifact is invalid or the user explicitly requests regeneration.

## Final delivery

A complete project should include at least:

```text
outputs/final/<project-name>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
outline/outline.json
outline/chapter-map.csv
chapters/*/script.md
chapters/*/shots.json
manifests/assets.jsonl
manifests/facts.jsonl
```

Before declaring completion, verify duration, chapter order, unresolved `NEEDS_SOURCE` markers, placeholders, missing assets, hash changes, subtitle/narration/video sync, loudness, chapter transitions, attribution, and the assembly report.

Never claim that an MP4 was completed unless the actual render and assembly succeeded.

## Prohibited shortcuts

- Do not use one giant prompt to generate the entire long-form script.
- Do not push all unfiltered source material into one context.
- Do not render the entire long-form program as one uncheckpointed task.
- Do not automatically approve downloaded media.
- Do not bypass authentication, paywalls, CAPTCHAs, regional restrictions, robots rules, or DRM.
- Do not skip fact checking because many sources exist.
- Do not overwrite original source media.
- Do not commit API keys, model weights, original media, rendered video/audio, or large caches.
