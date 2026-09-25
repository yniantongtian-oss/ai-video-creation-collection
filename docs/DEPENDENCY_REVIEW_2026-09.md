# Dependency review — 2026-09-25

This review refreshes the reproducibility pins used by the web-media and long-form production stacks. It records what was checked before moving the lock files; it is not a claim that every heavyweight application was rendered end-to-end in GitHub CI.

## Web-media pins

| Dependency | Previous pin | Reviewed pin | Upstream delta | Compatibility check |
|---|---|---|---:|---|
| yt-dlp | `fdcc954d` | `c7fb478d` | 53 commits | Git-installable project; CLI contract retained |
| gallery-dl | `8939a870` | `19a64031` | 5 commits | release/version update; CLI contract retained |
| Trafilatura | `467fdb38` | `07fe0d64` | 28 commits | Git-installable project; extractor CLI retained |
| MoneyPrinterTurbo | `42f776e2` | `ad5496f1` | 250 commits | `config.example.toml`, `pyproject.toml`, `uv.lock`, official Skill and helper all present |
| NarratoAI | `a9e17d0e` | `9fa69e02` | 6 commits | source delta is documentation-only; `config.example.toml` retained |
| VideoLingo | `968268bb` | `9bc30202` | 18 commits | `setup_env.py` retained; setup/ASR/audio changes require runtime smoke testing |

The installer still checks out exact commits and refuses to overwrite dirty local clones.

## MoneyPrinterTurbo Skill integrity

The reviewed upstream Skill remains version `1.3.2`.

- reviewed project commit: `ad5496f1b729d1d7e361dd972015d26c08b0e052`
- `docs/skill/SKILL.md` blob: `a14ae6b4f11743d2e362cb357797d7aae000a8ee`
- `docs/skill/mpt_agent.py` blob: `b7eb6cfedbeb453d10b891f21e572c10503a8d9f`

The local bootstrap downloads the helper from the exact reviewed commit and validates its Git blob SHA before execution. The reviewed helper adds additional video providers that can create paid jobs. The local Skill therefore requires explicit user confirmation before passing any provider-specific charge-confirmation flag.

## Long-form Python runtime

`pypdf` is refreshed from 6.14.2 to 6.19.0. `python-docx` 1.2.0, `edge-tts` 7.2.8, and `imageio-ffmpeg` 0.6.0 remain pinned because no newer reviewed release was selected in this pass.

## Validation boundary

Repository CI should validate lock-file JSON, Python compilation, dry-run installers/configurators, CLI entry points, workflow materialization, and project scaffolders. Real GPU inference, paid API calls, third-party stock downloads, and full video rendering remain explicit runtime tests and must not be represented as CI-verified unless they actually execute.
