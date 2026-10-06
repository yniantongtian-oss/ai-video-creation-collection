# Heavyweight Video Application Setup

`scripts/install_web_media_stack.py` downloads third-party tools at pinned commits into `tools/web-media/`. MoneyPrinterTurbo, NarratoAI, and VideoLingo can have large Python dependency sets, so runtime configuration is handled separately:

```bash
python scripts/configure_web_media_apps.py --app all
```

Preview without modifying files:

```bash
python scripts/configure_web_media_apps.py --app all --dry-run
```

## Configure individual applications

### MoneyPrinterTurbo

```bash
python scripts/install_web_media_stack.py --profile creator
python scripts/configure_web_media_apps.py --app moneyprinterturbo
```

The configurator:

1. Verifies that local Git HEAD matches the pinned commit in `tools/web-media-stack.lock.json`.
2. Runs `uv sync --frozen`.
3. Creates `config.toml` from `config.example.toml` when needed.
4. Never writes or prints API keys.

Then load:

```text
skills/moneyprinterturbo-video
```

The official Agent Skill detects missing LLM and Pexels credentials only when generation requires them and requests only the fields that are actually needed.

### NarratoAI

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/configure_web_media_apps.py --app narratoai
```

The configurator runs the official local setup:

```bash
uv sync
```

It also creates a local `config.toml` from `config.example.toml`. After editing the configuration:

```bash
cd tools/web-media/apps/NarratoAI
uv run streamlit run webui.py --server.maxUploadSize=2048
```

Open:

```text
http://127.0.0.1:8501
```

### VideoLingo

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/configure_web_media_apps.py --app videolingo
```

The configurator calls the installer provided by the pinned upstream version:

```bash
python setup_env.py --yes --skip-demucs
```

Demucs is skipped by default to reduce initial installation size. To include vocal separation:

```bash
python scripts/configure_web_media_apps.py \
  --app videolingo \
  --include-demucs
```

Windows launch command:

```text
OneKeyStart.bat
```

macOS / Linux:

```bash
cd tools/web-media/apps/VideoLingo
.venv/bin/streamlit run st.py
```

## Configuration safety

- Third-party application directories, virtual environments, models, caches, and local configuration are Git-ignored.
- The configurator does not overwrite an existing `config.toml`.
- It refuses to run when a third-party source tree has uncommitted changes, reducing the risk of mixing unknown modifications into a reviewed environment.
- Dependency installation still contacts PyPI, model hosts, and third-party services. Enterprise or high-security environments should review dependency locks, SBOMs, and network policy first.
- Some NarratoAI and VideoLingo features call external APIs or upload media. Review privacy, content, pricing, and commercial-use terms before enabling them.

## Hardware notes

- Common MoneyPrinterTurbo asset, Edge TTS, and FFmpeg workflows typically do not require a discrete GPU; API and encoding performance still depends on the environment.
- Basic NarratoAI flows can run on CPU, while local vision, speech, and cloning models may substantially increase RAM, storage, and VRAM requirements.
- VideoLingo workflows involving WhisperX, PyTorch, Demucs, or local dubbing are heavier. An NVIDIA GPU can accelerate some local tasks; compatibility depends on the pinned upstream installer.
