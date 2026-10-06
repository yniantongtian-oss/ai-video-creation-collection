# 60–360 Minute Long-Form Video Production Guide

This guide covers hour-plus documentaries, explainers, courses, historical narratives, investigative pieces, feature commentary, and other multi-chapter productions.

Long-form video should not be produced as one giant short-video prompt. The recommended approach is: **research by chapter, write by chapter, narrate by chapter, render by chapter, then assemble the final program**.

## 1. Why chapter-based production is required

A 90-minute project can require roughly 13 chapters and about 540 visual segments if the main visual changes every 10 seconds. A real production may also include:

- dozens or hundreds of source documents;
- hundreds or thousands of candidate images, videos, and audio assets;
- hundreds of factual claims and source references;
- repeated model calls;
- many narration and subtitle segments;
- large intermediate caches;
- tens of GiB of temporary files.

The default workflow therefore splits a 90-minute project into chapters of roughly seven minutes. If one chapter fails, rerun only that chapter.

## 2. Install

Install research and media tools:

```bash
python scripts/install_web_media_stack.py --profile full
```

Install the long-form runtime:

```bash
python scripts/install_longform_stack.py
```

Install Auto-Editor:

```bash
python scripts/install_auto_editor.py
```

Preview the long-form installation plan:

```bash
python scripts/install_longform_stack.py --dry-run
```

Runtime:

```text
tools/longform/.venv
```

Local configuration:

```text
tools/longform/.env
```

The runtime directory and secrets are not committed to Git.

## 3. Configure the language model

Edit:

```text
tools/longform/.env
```

Provide an OpenAI-compatible Chat Completions endpoint:

```text
LONGFORM_LLM_BASE_URL=https://your-service.example/v1
LONGFORM_LLM_API_KEY=your-key
LONGFORM_LLM_MODEL=your-model
```

Prefer a model that:

- reliably returns structured JSON;
- provides sufficient context length;
- can produce coherent long-form prose;
- supports adequate output length;
- has manageable pricing and rate limits.

Never place secrets in project scripts, logs, README files, or commits.

## 4. Create a project

Example 90-minute documentary:

```bash
python scripts/scaffold_longform_project.py \
  --name "space-solar-power-documentary" \
  --topic "History, principles, engineering approaches, debates, and future of space-based solar power" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --audience "General viewers interested in technology" \
  --style "Documentary explainer with high information density and natural narration"
```

Example two-hour project:

```bash
python scripts/scaffold_longform_project.py \
  --name "two-hour-feature" \
  --topic "Feature topic" \
  --duration 120 \
  --chapter-minutes 8 \
  --aspect-ratio 16:9
```

Project structure:

```text
projects/<project-name>/
├── brief.md
├── project.json
├── research/
│   ├── inbox/
│   ├── extracted/
│   ├── summaries/
│   ├── sources.jsonl
│   ├── chunks.jsonl
│   └── index.sqlite
├── outline/
│   ├── outline.json
│   └── chapter-map.csv
├── assets/
├── manifests/
│   ├── assets.jsonl
│   ├── facts.jsonl
│   └── render.jsonl
├── chapters/
│   ├── 01/
│   ├── 02/
│   └── ...
├── state/
├── logs/
└── outputs/
```

## 5. Prepare research material

Place source material in:

```text
projects/<project-name>/research/inbox/
```

Supported inputs include PDF, DOCX, PPTX, TXT, Markdown, HTML, CSV, TSV, JSON, SRT, VTT, and extracted web documents.

A balanced research set should include authoritative primary sources, original papers or technical reports, standards or policy documents where relevant, institutional or archival material, high-quality journalism for background, expert interviews, user notes, and credible counterarguments. Do not collect only material that supports one conclusion.

To ingest a web document:

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/article" \
  --project "projects/<project-name>" \
  --asset-id "source-example" \
  --license "reference-only" \
  --rights-status restricted
```

Research use and media-reuse rights are separate. A web page may support factual research without granting reuse rights for its images or video.

## 6. Build the research corpus

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<project-name>"
```

Add external directories:

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<project-name>" \
  --input "/path/to/documents" \
  --input "/path/to/subtitles"
```

Rebuild the index:

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<project-name>" \
  --reset-index
```

The ingester calculates SHA-256 hashes, skips duplicates, preserves page or slide references, extracts text, chunks content with overlap, writes JSONL, and builds a SQLite full-text index.

Scanned PDFs without a text layer require OCR before ingestion. Do not treat an empty extraction as successfully read content.

## 7. Generate summaries, outline, scripts, and shot plans

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  research
```

Processing order:

```text
Per-source summaries
→ full-program chapter outline
→ per-chapter retrieval
→ per-chapter script
→ per-chapter shot plan
```

Main outputs:

```text
research/summaries/*.md
outline/outline.json
outline/chapter-map.csv
chapters/*/script.md
chapters/*/narration.txt
chapters/*/claims.json
chapters/*/open-questions.json
chapters/*/shots.json
```

`script.md` preserves source markers such as:

```text
[S:source-id#page=12;chunk=3]
```

`narration.txt` contains the spoken text without those markers.

Rewrite one chapter:

```bash
python scripts/longform_pipeline.py \
  --project "projects/<project-name>" \
  write \
  --chapter 4 \
  --force
```

Rebuild that chapter's shot plan:

```bash
python scripts/longform_pipeline.py \
  --project "projects/<project-name>" \
  shots \
  --chapter 4 \
  --force
```

## 8. Estimate asset volume

A rough planning table for one major visual change every 10 seconds:

| Final duration | Visual segments | Suggested distinct assets |
|---|---:|---:|
| 60 minutes | about 360 | 120–220 |
| 90 minutes | about 540 | 180–320 |
| 120 minutes | about 720 | 240–420 |
| 180 minutes | about 1,080 | 350–600 |

Reasonable reuse can include alternate crops, slow push-ins, detail zooms, captions, maps, or timeline overlays, but avoid long repetitive sequences.

## 9. Build the asset search plan

```bash
python scripts/build_longform_asset_plan.py \
  --project "projects/<project-name>"
```

Execute open-media search:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  assets \
  --execute-search \
  --download-first 1
```

Increase candidate volume only when needed:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  assets \
  --execute-search \
  --download-first 3 \
  --search-limit 12
```

Supported discovery providers include Wikimedia Commons, Openverse, Pexels, and Pixabay.

Automatically downloaded items are candidates only and are not approved for final use by default.

## 10. Add user-owned media

```bash
python scripts/media_asset_manifest.py add \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --id "my-interview-001" \
  --kind video \
  --local-path "assets/global/videos/interview.mp4" \
  --license "User owned" \
  --rights-status user-owned \
  --permission-note "Recorded by the project team and cleared for this production" \
  --title "Expert interview"
```

User-owned media should include clear ownership or permission notes.

## 11. Review and approve candidate assets

List candidates:

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --candidates
```

Approve one item:

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "Verified content, source page, license, and attribution requirements"
```

Bulk approval:

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<project-name>/manifests/assets.jsonl" \
  --ids-file approved-assets.txt \
  --value true
```

Approval checks file existence, SHA-256 integrity, rights status, HTTPS provenance for non-local assets, attribution metadata for CC BY/CC BY-SA, and permission notes for user-owned or separately licensed media.

## 12. Narration

```bash
python scripts/render_longform_narration.py \
  --project "projects/<project-name>"
```

Use an appropriate available voice for the target language and audience:

```bash
python scripts/render_longform_narration.py \
  --project "projects/<project-name>" \
  --voice en-US-JennyNeural
```

Rerun one chapter:

```bash
python scripts/render_longform_narration.py \
  --project "projects/<project-name>" \
  --chapter 4 \
  --force
```

Each chapter is split into narration segments with aligned subtitles. Failed segments can be retried independently.

## 13. Build the timeline

```bash
python scripts/build_longform_timeline.py \
  --project "projects/<project-name>"
```

The timeline builder uses only approved media and matches assets using shot queries, narration keywords, titles/descriptions, media type, chapter assignment, and recent reuse.

If approved media is insufficient, the pipeline should fail. For internal previews only:

```bash
python scripts/build_longform_timeline.py \
  --project "projects/<project-name>" \
  --allow-placeholders
```

Placeholders must never appear in a final release.

## 14. Render chapters

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<project-name>"
```

Process:

```text
Normalize each shot to the target format
→ concatenate shot visuals
→ mix narration and optional licensed background music
→ write subtitle track
→ output chapter MP4
```

Rerun chapter four:

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<project-name>" \
  --chapter 4 \
  --force
```

Burn subtitles when required:

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<project-name>" \
  --burn-subtitles
```

Add licensed background music:

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<project-name>" \
  --bgm "/path/to/licensed-bgm.mp3"
```

Background music must have clear reuse rights.

## 15. Assemble the final program

```bash
python scripts/assemble_longform_video.py \
  --project "projects/<project-name>"
```

Outputs:

```text
outputs/final/<project-name>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
```

Lossless stream-copy concatenation is preferred when chapter parameters match; otherwise the pipeline falls back to re-encoding.

## 16. Production command

After assets are reviewed and approved:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  produce
```

This runs:

```text
Rights and resource preflight
→ per-chapter narration
→ per-chapter timeline
→ per-chapter render
→ final assembly
```

If asset review is incomplete, the pipeline stops with:

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

This is an intentional safety gate.

## 17. Full run from research input

After populating `research/inbox/`:

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  all \
  --execute-search \
  --download-first 1
```

The run stops at the asset-review gate. After approval, run `produce`.

## 18. Status and checkpoints

```bash
python scripts/run_longform_project.py \
  --project "projects/<project-name>" \
  status
```

State files:

```text
state/pipeline.json
chapters/<number>/status.json
```

Valid existing summaries, outlines, chapter scripts, shot plans, narration segments, shot caches, rendered chapters, and final outputs are skipped by default. Use `--force` only when necessary.

## 19. Preflight checks

Before research:

```bash
python scripts/longform_preflight.py \
  --project "projects/<project-name>" \
  --stage setup
```

Before rendering:

```bash
python scripts/longform_preflight.py \
  --project "projects/<project-name>" \
  --stage render
```

Before final assembly:

```bash
python scripts/longform_preflight.py \
  --project "projects/<project-name>" \
  --stage final
```

Preflight checks estimate final size and temporary storage, inspect free disk space, verify script and shot completeness, validate asset rights, detect placeholders, compare narration and chapter timing, and count rendered chapters.

## 20. Storage and performance

For a 90-minute 1080p project, allow several times the expected final file size for source media, caches, intermediate chapters, and retries, plus separate space for models.

Recommended:

- keep active projects on SSD storage;
- separate source-media storage from caches when possible;
- test one chapter before rendering the full project;
- use faster encoding presets during iteration;
- avoid storing video or audio inside the Git repository;
- regularly back up `project.json`, research material, scripts, shot plans, and asset manifests.

## 21. Final quality checklist

Before release, verify at minimum:

1. Total duration is correct.
2. Chapter order and transitions are correct.
3. Scripts do not contain obvious repetition.
4. Important factual claims have sources.
5. All `NEEDS_SOURCE` markers are resolved.
6. Names, dates, locations, numbers, and quotations are verified.
7. Visuals match the narration.
8. No incorrect people, places, periods, or equipment appear.
9. No unapproved or unknown-source media remains.
10. Required attribution is complete.
11. There are no long black frames, accidental stills, or excessive repetition.
12. Narration volume is consistent.
13. Background music does not mask speech.
14. Subtitle timing and segmentation are reviewed.
15. Chapter timestamps are correct.
16. `assembly-report.json` passes duration checks.
17. The opening, middle, ending, and chapter boundaries are spot-checked.
18. Platform and commercial-use rules are reviewed before upload.

## 22. Example Codex instruction

```text
Load skills/longform-documentary-producer.

Produce a 90-minute 16:9 documentary about <topic>.
Create the project first and ingest everything in research/inbox into a corpus that preserves
SHA-256 hashes, page numbers, and slide references. Summarize each source, design a roughly
13-chapter outline, then retrieve, write, and build a shot plan for each chapter separately.
Important factual claims must retain source markers. Write NEEDS_SOURCE when evidence is
insufficient instead of guessing.

Find images, video, and audio from Wikimedia Commons, Openverse, Pexels, Pixabay, and user-owned
sources. Automatically downloaded media is candidate-only until its content, source page, and
license are reviewed and selected=true is explicitly approved. Unknown or restricted assets
must not enter the final program.

After review, generate narration and subtitles by chapter, match approved media, and render each
chapter independently. If one chapter fails, rerun only that chapter. Assemble the final MP4 and
deliver full.srt, chapter timestamps, chapter metadata, scripts, shot plans, factual-claim records,
the media-rights manifest, and assembly-report.json. Do not claim the final program exists unless
the final MP4 was actually generated.
```
