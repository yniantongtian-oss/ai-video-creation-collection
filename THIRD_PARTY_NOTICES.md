# Third-Party Notices

This file records third-party material that is copied, adapted, or downloaded by scripts. The MIT license at the repository root applies only to original content in this repository and does not alter the licenses of third-party projects, model weights, binary components, or media.

## Auto-Editor Agent Skills

- Upstream project: `WyattBlue/auto-editor`
- Upstream URL: <https://github.com/WyattBlue/auto-editor>
- Import date: 2026-07-29
- Upstream license: Unlicense / public-domain dedication
- Upstream license file: <https://github.com/WyattBlue/auto-editor/blob/master/LICENSE>

Imported files:

| Repository file | Upstream file | Upstream blob SHA at import |
|---|---|---|
| `skills/auto-editor/SKILL.md` | `skills/auto-editor/SKILL.md` | `0b23e0d1b7e6268d45f40c528dc9c684cf5bf501` |
| `skills/auto-editor-effects/SKILL.md` | `skills/auto-editor-effects/SKILL.md` | `2bc16875a5f9321e948049726e2e2b44cefd0d08` |
| `skills/auto-editor-export/SKILL.md` | `skills/auto-editor-export/SKILL.md` | `cb99014f41ccab06875bb067b3ab102bd20c5e40` |
| `skills/auto-editor-transcribe/SKILL.md` | `skills/auto-editor-transcribe/SKILL.md` | `830259ec762c091be35ad313fcf4d4803e5d2dcf` |

The upstream license permits copying, modification, publication, use, compilation, sale, and distribution of the software and provides it "as is" without express or implied warranty. Refer to the upstream `LICENSE` file for the complete legal text.

## Auto-Editor Release Binaries

`scripts/install_auto_editor.py` does not host binaries in this repository. At runtime it downloads the appropriate asset for the current platform from the official GitHub Releases page:

- <https://github.com/WyattBlue/auto-editor/releases>

Official builds currently use asset names such as:

```text
auto-editor-linux-x86_64
auto-editor-linux-aarch64
auto-editor-linux-armv7
auto-editor-macos-x86_64
auto-editor-macos-arm64
auto-editor-windows-x86_64.exe
auto-editor-windows-aarch64.exe
```

Release binaries may include FFmpeg, codecs, transcription components, or other dependencies under their own licenses. Review the release notes, build configuration, and license information for the downloaded version. The download script records the source version and asset URL but is not a substitute for digital-signature or independent supply-chain verification.

## MoneyPrinterTurbo Agent Skill

- Upstream project: `harry0703/MoneyPrinterTurbo`
- Upstream URL: <https://github.com/harry0703/MoneyPrinterTurbo>
- Reviewed commit: `ad5496f1b729d1d7e361dd972015d26c08b0e052`
- Upstream license: MIT
- Upstream Skill: `docs/skill/SKILL.md`
- Upstream Skill blob SHA: `a14ae6b4f11743d2e362cb357797d7aae000a8ee`
- Upstream helper: `docs/skill/mpt_agent.py`
- Upstream helper blob SHA: `b7eb6cfedbeb453d10b891f21e572c10503a8d9f`

`skills/moneyprinterturbo-video/SKILL.md` adapts the official upstream Skill for this repository and adds media-license review gates plus Linux capability boundaries.

This repository does not copy the full upstream helper. `skills/moneyprinterturbo-video/mpt_agent.py` is an original minimal bootstrapper that downloads the official helper from the pinned commit, verifies it using its Git blob SHA-1, and then executes it. Re-review upstream code before changing the pinned commit or SHA.

## Web Media Stack External Dependencies

`scripts/install_web_media_stack.py` installs or clones third-party tools into the Git-ignored `tools/web-media/` directory according to `tools/web-media-stack.lock.json`. Those projects are not covered by this repository's MIT license.

| Project | Pinned commit | License | Purpose |
|---|---|---|---|
| `yt-dlp/yt-dlp` | `c7fb478d21e9e59524befbe23f7801bb267fb880` | Unlicense | Download public or authorized video, audio, subtitles, and metadata |
| `mikf/gallery-dl` | `19a64031b7e695dc76d7d689a1c9d7470fc0bfc7` | GPL-2.0 | Download public or authorized image galleries as an external command |
| `adbar/trafilatura` | `07fe0d6497f30fc6a91f0e591cf8623f2aba427b` | Apache-2.0 | Extract web-page text and metadata |
| `harry0703/MoneyPrinterTurbo` | `ad5496f1b729d1d7e361dd972015d26c08b0e052` | MIT | Script, licensed media, voice-over, subtitles, music, and short-video assembly |
| `linyqh/NarratoAI` | `9fa69e022d4add41205ee385207561df8796b3f1` | MIT | Existing-video understanding, commentary writing, and automated editing |
| `Huanshere/VideoLingo` | `9bc30202ad87f87e2ecbdfb1cc25d5b9d62849e3` | Apache-2.0 | Video translation, subtitles, localization, and dubbing |

The installer does not automatically accept third-party licenses, API terms, or model terms. Review the licenses and documentation at the pinned commits before use. Third-party applications may download additional Python packages, models, FFmpeg builds, speech components, or frontend dependencies under separate licenses.

Paid video-generation providers exposed by the reviewed MoneyPrinterTurbo helper (including Seedance, WaveSpeed, OFox, Metaso MiniMax, and MuAPI) require explicit per-provider charge confirmation in the local Skill wrapper. API availability does not authorize the wrapper to accept billable jobs automatically.

## Long-Form Production Runtime

`scripts/install_longform_stack.py` installs these pinned versions into the Git-ignored `tools/longform/.venv` directory according to `tools/longform-stack.lock.json`:

| Project | Version | Upstream | License | Purpose |
|---|---:|---|---|---|
| `pypdf` | `6.19.0` | <https://github.com/py-pdf/pypdf> | BSD-3-Clause | PDF text extraction and page-number references |
| `python-docx` | `1.2.0` | <https://github.com/python-openxml/python-docx> | MIT | Read DOCX paragraphs and tables |
| `edge-tts` | `7.2.8` | <https://github.com/rany2/edge-tts> | LGPL-3.0 | Per-chapter voice-over and SRT subtitle generation |
| `imageio-ffmpeg` | `0.6.0` | <https://github.com/imageio/imageio-ffmpeg> | BSD-2-Clause | Cross-platform FFmpeg executable fallback |

`edge-tts` uses an online speech service. A software license does not automatically grant commercial rights to the service, voice, or generated output. Check current service terms before publication.

The `imageio-ffmpeg` Python package license is separate from the licenses of the FFmpeg build and codecs bundled in platform wheels. Check the actual downloaded build, enabled codecs, FFmpeg license, and delivery-region requirements. This repository does not provide legal advice.

OCR for scanned PDFs, fonts, background music, model services, and other components installed separately by users are not part of the pinned long-form dependency list and remain subject to their own licenses and service terms.

## Stock and Open Media Providers

`scripts/search_open_media.py` can query Wikimedia Commons, Openverse, Pexels, and Pixabay APIs. License data in search results is preliminary metadata; verify the original source page before final use.

- Wikimedia Commons files may require attribution, share-alike terms, or other page-specific conditions.
- Openverse is a discovery layer; the original host remains authoritative for the file and license status.
- Pexels content is subject to the Pexels License and API terms, and creator attribution and links are encouraged.
- Pixabay content is subject to the Pixabay Content License and API terms; display and bulk-download behavior is restricted by API policy.

This repository does not grant copyright in third-party media and does not guarantee that any asset is suitable for commercial use, advertising, identifiable-person use, trademarks, or sensitive contexts.

## Speech Models

This repository does not host Whisper, WhisperX, Parakeet, GPT-SoVITS, IndexTTS, or other speech-model weights. Users who download models separately must verify the applicable terms for model weights, datasets, code, voice cloning, and generated output.
