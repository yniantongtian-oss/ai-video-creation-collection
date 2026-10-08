# Web Research and Automated Media Production

This repository supports an end-to-end workflow:

```text
Public web research
→ document extraction and fact checking
→ openly licensed image/video/audio search
→ authorized-link downloads
→ source and license manifests
→ script, storyboard, narration, subtitles, and music
→ automated editing, dubbing, or commentary
→ final MP4 and traceable delivery package
```

Primary entry point:

```text
skills/web-media-producer
```

Topic-to-video entry point:

```text
skills/moneyprinterturbo-video
```

## 1. Install

Install `git` and `uv`, then run from the repository root:

```bash
python scripts/install_web_media_stack.py --profile creator
```

Profiles:

| Profile | Includes | Best for |
|---|---|---|
| `core` | yt-dlp, gallery-dl, Trafilatura | Research, downloads, asset archiving |
| `creator` | core + MoneyPrinterTurbo | Topic/script/assets/narration/subtitles to short video |
| `full` | creator + NarratoAI + VideoLingo | Commentary, existing-video analysis, translation, multilingual dubbing |

Preview commands and pinned versions:

```bash
python scripts/install_web_media_stack.py --profile full --dry-run
```

Third-party programs are installed into:

```text
tools/web-media/
```

That directory is Git-ignored. The repository stores only reviewed repository URLs, commit SHAs, license information, and installation instructions in:

```text
tools/web-media-stack.lock.json
```

## 2. API keys

Initial setup creates:

```text
tools/web-media/.env
```

Template:

```text
config/web-media.env.example
```

Common fields:

```text
MPT_LLM_PROVIDER=moonshot
MPT_LLM_API_KEY=
MPT_PEXELS_API_KEY=
PEXELS_API_KEY=
PIXABAY_API_KEY=
```

Never commit real secrets, place them in scripts, print them to logs, or send them to untrusted services.

MoneyPrinterTurbo's official Skill reuses existing configuration and requests only credentials that are missing and necessary.

## 3. Create a project

```bash
python scripts/scaffold_web_media_project.py \
  --name "space-solar-power-explainer" \
  --topic "How space-based solar power could transmit energy to Earth" \
  --duration 90 \
  --aspect-ratio 9:16 \
  --language en-US
```

Generated structure:

```text
projects/space-solar-power-explainer/
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

`projects/` is Git-ignored by default so media, secrets, caches, and large rendered files are not committed.

## 4. Search open media

### Wikimedia Commons

```bash
python scripts/search_open_media.py \
  --provider commons \
  --media-type image \
  --query "space based solar power" \
  --limit 20 \
  --output "projects/space-solar-power-explainer/research/search-results/commons.json"
```

The tool reads Commons file pages and extended license metadata. Manually review each source page because historical uploads, attribution, and derivative works may impose additional requirements.

### Openverse

```bash
python scripts/search_open_media.py \
  --provider openverse \
  --media-type image \
  --query "solar power satellite" \
  --limit 20
```

Openverse helps discover Creative Commons and public-domain media. The original source page remains authoritative for licensing.

### Pexels

```bash
python scripts/search_open_media.py \
  --provider pexels \
  --media-type video \
  --query "satellite earth solar panels" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/space-solar-power-explainer/assets/videos" \
  --manifest "projects/space-solar-power-explainer/manifests/assets.jsonl"
```

Pexels requires an API key. Preserve source links and credit creators when appropriate.

### Pixabay

```bash
python scripts/search_open_media.py \
  --provider pixabay \
  --media-type video \
  --query "satellite energy" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/space-solar-power-explainer/assets/videos" \
  --manifest "projects/space-solar-power-explainer/manifests/assets.jsonl"
```

Pixabay requires an API key. The script downloads candidate assets instead of hotlinking and records the relevant license page.

## 5. Collect public web sources

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/official-document" \
  --project "projects/space-solar-power-explainer" \
  --asset-id "official-source-001" \
  --license "Research reference; quotation limits apply" \
  --rights-status restricted
```

Extracted Markdown is stored in:

```text
research/documents/
```

`restricted` means the source may be used for research and fact checking, but substantial source text should not be republished as narration or visual media.

## 6. Download user-authorized media

Public video:

```bash
python scripts/ingest_authorized_source.py \
  --type video \
  --url "https://example.com/public-video" \
  --project "projects/project-name" \
  --asset-id "user-video-001" \
  --license "User owns or has permission to reuse" \
  --rights-status permission-granted \
  --permission-note "User confirmed permission to reuse"
```

Public gallery:

```bash
python scripts/ingest_authorized_source.py \
  --type gallery \
  --url "https://example.com/gallery" \
  --project "projects/project-name" \
  --asset-id "gallery-001" \
  --license "CC BY 4.0" \
  --license-url "https://creativecommons.org/licenses/by/4.0/" \
  --rights-status cc-by \
  --creator "Creator Name" \
  --attribution "Creator Name, CC BY 4.0"
```

The downloader wrapper does not expose cookie, account-password, browser-session, or DRM-bypass options.

## 7. Asset manifest and rights gate

Validate the manifest:

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

Automatically downloaded search results are stored as candidates:

```json
"selected": false
```

Before changing an asset to `selected=true`, review the content, resolution, relevance, privacy implications, and licensing.

## 8. Generate scripts and video

### MoneyPrinterTurbo: topic-to-video

From `skills/moneyprinterturbo-video`:

```bash
uv run --no-project --python 3.11 python mpt_agent.py \
  --subject "How space-based solar power works"
```

The default workflow targets an English-language 9:16 video using licensed stock media, Edge TTS, subtitles, and background music.

### Auto-Editor: edit selected footage

Load:

```text
skills/ai-video-editing
```

Preview edit decisions before rendering a new file, and never overwrite the source. Export to Premiere, DaVinci Resolve, Final Cut Pro, Shotcut, or Kdenlive when manual refinement is needed.

### NarratoAI: commentary on existing video

Installed at:

```text
tools/web-media/apps/NarratoAI
```

Use it only with user-owned, public-domain, or otherwise authorized footage.

### VideoLingo: translation and dubbing

Installed at:

```text
tools/web-media/apps/VideoLingo
```

Use it for transcription, translation, terminology consistency, dubbing, and localization of authorized video.

## 9. Example production sequence

For a short educational video, gather authoritative source material, save full provenance for approved media, draft an original script, prepare a shot-by-shot storyboard, and verify factual claims. Record the license, authorization status, and attribution requirements of each asset before rendering.

Produce narration, captions, and a rough edit using available tools. Review pacing, information accuracy, output quality, and media rights. Deliver the final video alongside source, attribution, and project manifests.

## 10. Capability boundaries

This setup can research and organize public web material, but it does not promise to:

- Crawl the entire internet.
- Bypass platform restrictions, authentication, CAPTCHAs, paywalls, or DRM.
- Acquire copyright in third-party video, images, music, or articles automatically.
- Eliminate the need for human review of subtitles, facts, asset licensing, and final edits.
- Claim a finished video exists unless the generation workflow actually ran.

Commercial, news, medical, legal, financial, reputational, and controversial content requires stricter source and rights review.
