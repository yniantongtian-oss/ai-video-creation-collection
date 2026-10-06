---
name: web-media-producer
description: Collect documents, images, video, and audio from public web sources, openly licensed media libraries, and user-authorized URLs; preserve provenance and licensing; fact-check the project; write an original script and shot list; produce narration, subtitles, edits, and final video. Use for research-driven explainers, news context, product videos, commentary, mixed-source edits, and video localization. Prefer openly licensed and user-authorized sources. Do not bypass authentication, paywalls, DRM, robots rules, regional controls, or platform safeguards.
metadata:
  version: 1.1.0
  language: en-US
  orchestrates:
    - moneyprinterturbo-video
    - ai-video-editing
    - NarratoAI
    - VideoLingo
    - yt-dlp
    - gallery-dl
    - Trafilatura
---

# Web Research and Media Production

Convert the user's goal into a traceable production pipeline:

```text
Topic and audience
→ web research and source verification
→ openly licensed or authorized media search
→ asset manifest and rights gate
→ original script and shot-by-shot storyboard
→ narration, subtitles, and music
→ automated rough cut and packaging
→ video, project files, source manifest, and fact-check report
```

"Web research" means broad research across public and permitted sources, not unbounded crawling. Technical ability to download media does not grant the right to copy, modify, or republish it.

## 1. Runtime setup

For ordinary research and topic-to-video work:

```bash
python scripts/install_web_media_stack.py --profile creator
python scripts/check_video_editing_tools.py
```

For commentary, existing-video analysis, translation, and multilingual dubbing:

```bash
python scripts/install_web_media_stack.py --profile full
```

Configure applications only when needed:

```bash
python scripts/configure_web_media_apps.py --app moneyprinterturbo
python scripts/configure_web_media_apps.py --app narratoai
python scripts/configure_web_media_apps.py --app videolingo
```

Or configure all supported applications:

```bash
python scripts/configure_web_media_apps.py --app all
```

Preview without changing the environment:

```bash
python scripts/install_web_media_stack.py --profile full --dry-run
python scripts/configure_web_media_apps.py --app all --dry-run
```

VideoLingo skips optional Demucs by default. Add `--include-demucs` only when vocal separation is required.

See `docs/WEB_MEDIA_APP_SETUP.md` for runtime details.

Secrets belong in:

```text
tools/web-media/.env
```

This file is created from `config/web-media.env.example` and is Git-ignored. Never print, commit, or repeat API keys, tokens, or full credential-bearing configuration.

## 2. Create the project first

```bash
python scripts/scaffold_web_media_project.py \
  --name "project-name" \
  --topic "research topic" \
  --duration 60 \
  --aspect-ratio 9:16 \
  --language en-US
```

Project structure:

```text
projects/<name>/
├── brief.md
├── project.json
├── research/
├── assets/
├── manifests/assets.jsonl
├── script/script.md
├── storyboard/storyboard.csv
├── edit/edit-plan.json
├── subtitles/
├── voice/
└── outputs/
```

Keep intermediate artifacts inside the project directory instead of scattering them across the repository root.

## 3. Define requirements

Reuse information the user already provided. Establish:

- `topic`: subject or core question;
- `goal`: explainer, marketing, news context, tutorial, story, commentary, or localization;
- `audience`: expected knowledge level;
- `duration`: target length;
- `aspect_ratio`: 9:16, 16:9, 1:1, or 4:5;
- `language`: script, narration, and subtitle language;
- `platform`: YouTube, TikTok, Instagram, web, or another named destination;
- `source_scope`: open web, specified sites, user files, or URLs;
- `commercial_use`: whether commercial use is intended;
- `delivery`: video, subtitles, script, editing project, and source/rights manifests.

When minor information is missing but work can proceed safely, document explicit assumptions in `brief.md`.

## 4. Web research

Research principles:

1. Prefer primary sources, official documentation, papers, institutional pages, and reputable journalism.
2. Search-result snippets are for discovery only; verify the original source.
3. Record title, URL, author/organization, publication date, and limitations for important claims.
4. Do not reproduce full articles, transcripts, book chapters, or paywalled content. Preserve only necessary summaries and short quotations.
5. Verify time-sensitive claims such as news, prices, policy, identity, software versions, and product specifications with current sources.
6. Preserve meaningful source disagreement rather than forcing contradictory evidence into a single certain conclusion.

Ingest a selected public document:

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/article" \
  --project "projects/project-name" \
  --asset-id "source-001" \
  --license "Research reference; quotation limits apply" \
  --rights-status restricted
```

A `restricted` document may support research and fact checking but must not be republished substantially as narration or visual media.

Do not crawl entire sites by default. Work with a small set of selected pages unless broad crawling is clearly allowed and necessary.

## 5. Media search and download

Prefer:

1. Wikimedia Commons files with clear public-domain or Creative Commons status;
2. Openverse results with verifiable licensing;
3. Pexels;
4. Pixabay;
5. supported provider-licensed sources such as Coverr where available;
6. user-owned media or links with explicit permission.

### Wikimedia Commons

```bash
python scripts/search_open_media.py \
  --provider commons \
  --media-type image \
  --query "space solar power station" \
  --limit 20 \
  --output "projects/project-name/research/search-results/commons.json"
```

### Pexels video candidates

```bash
python scripts/search_open_media.py \
  --provider pexels \
  --media-type video \
  --query "solar panels satellite earth" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/project-name/assets/videos" \
  --manifest "projects/project-name/manifests/assets.jsonl" \
  --output "projects/project-name/research/search-results/pexels.json"
```

### Pixabay image candidates

```bash
python scripts/search_open_media.py \
  --provider pixabay \
  --media-type image \
  --query "satellite energy" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/project-name/assets/images" \
  --manifest "projects/project-name/manifests/assets.jsonl"
```

Downloaded search results are candidates with `selected=false`. Review content, relevance, quality, privacy, provenance, and rights before selecting them.

### User-authorized video

```bash
python scripts/ingest_authorized_source.py \
  --type video \
  --url "https://example.com/public-video" \
  --project "projects/project-name" \
  --asset-id "user-video-001" \
  --license "User owns or has permission to reuse" \
  --rights-status permission-granted \
  --permission-note "User confirmed permission to reuse this media for the current project"
```

### User-authorized gallery

```bash
python scripts/ingest_authorized_source.py \
  --type gallery \
  --url "https://example.com/public-gallery" \
  --project "projects/project-name" \
  --asset-id "gallery-001" \
  --license "CC BY 4.0" \
  --license-url "https://creativecommons.org/licenses/by/4.0/" \
  --rights-status cc-by \
  --creator "Creator Name" \
  --attribution "Creator Name, CC BY 4.0"
```

Do not bypass authentication, regional controls, paywalls, DRM, private accounts, CAPTCHAs, or anti-abuse controls. The repository wrappers intentionally do not expose browser cookies, passwords, or DRM-bypass options.

## 6. Rights gate

Before the final edit:

```bash
python scripts/media_asset_manifest.py validate \
  --manifest "projects/project-name/manifests/assets.jsonl"
```

Allowed by default:

```text
public-domain
cc0
cc-by
cc-by-sa
provider-licensed
user-owned
permission-granted
```

Blocked by default:

```text
unknown
restricted
```

CC BY and CC BY-SA material must record creator and license URL. `permission-granted` items must include a permission note. Required attribution should appear in the credits, description, or delivery manifest as appropriate.

## 7. Script and storyboard

Write `script/script.md` with at least:

1. title candidates;
2. a 3–8 second opening hook;
3. context and problem framing;
4. core explanation or narrative progression;
5. evidence, data, and examples;
6. conclusion;
7. call to action when appropriate;
8. fact-check checklist.

The script should use original expression rather than stitching source sentences together or imitating a living creator's distinctive style.

Write `storyboard/storyboard.csv` with:

- start/end time;
- narration;
- visual search phrase;
- selected `asset_id`;
- crop, motion, zoom, and transition notes;
- subtitles;
- factual source references;
- status.

Every visual must support the narration semantically, not merely look attractive.

## 8. Choose a production route

### Route A: topic-to-short-video

Use `skills/moneyprinterturbo-video` for explainers, marketing, educational content, and social video that does not require exact per-shot assets.

MoneyPrinterTurbo can handle script generation, supported stock-media search, narration, subtitles, music, and rendering. Merge its final MP4, task directory, script, and media provenance into the current project.

### Route B: research-driven edit with selected media

Use `skills/ai-video-editing` when specific documents, images, videos, or a strict storyboard must be honored.

```text
Media preparation → narration → shot assembly → subtitles → music
→ automated rough cut → human spot-check → MP4 or professional editing project
```

### Route C: commentary on existing authorized video

Use the pinned NarratoAI installation:

```text
tools/web-media/apps/NarratoAI
```

Configure first:

```bash
python scripts/configure_web_media_apps.py --app narratoai
```

Use only with user-owned, public-domain, or otherwise authorized footage. Do not default to acquiring commercial film or television and republishing it.

### Route D: translation, subtitles, and dubbing

Use:

```text
tools/web-media/apps/VideoLingo
```

Configure first:

```bash
python scripts/configure_web_media_apps.py --app videolingo
```

Its capabilities may include yt-dlp input, WhisperX, subtitle segmentation, translation, terminology handling, and multiple TTS options. Verify the source video's reuse, translation, and publication rights.

## 9. Quality checks

Content:
- every important factual claim has a source;
- dates, numbers, people, and organizations are accurate;
- speculation is not presented as fact;
- source material is not reproduced excessively.

Media:
- `asset_id` matches the actual file;
- selected media passes manifest validation;
- required attribution is present;
- no unreviewed watermarks, privacy violations, sensitive information, or misleading imagery.

Video:
- sentence boundaries are not cut incorrectly;
- visuals align with narration;
- subtitle text and timing are spot-checked;
- narration is clear and music does not overpower speech;
- framing preserves the subject;
- final files play correctly and meet duration, resolution, and frame-rate requirements.

## 10. Deliverables

At minimum:

```text
outputs/final.mp4
script/script.md
storyboard/storyboard.csv
subtitles/final.srt
manifests/assets.jsonl
research/sources.md
edit/edit-plan.json
```

Also provide a concise report covering major research sources, media providers, attribution requirements, the chosen production route, steps that actually ran, and any remaining human-review items.

Never claim the video was generated unless the production workflow actually ran successfully. Do not render the final release when the rights gate has not passed.
