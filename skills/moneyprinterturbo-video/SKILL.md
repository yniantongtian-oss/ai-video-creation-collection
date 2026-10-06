---
name: moneyprinterturbo-video
description: Use MoneyPrinterTurbo to generate a complete video from a topic, title, idea, prompt, or script. Use for short explainers, marketing, narrated social video, installation/configuration, missing API credentials, generation failures, and locating the final MP4. The expected outcome is a rendered video, not merely setup instructions.
compatibility: Requires an agent with terminal, network, filesystem, and long-running foreground-command access. The upstream official Skill explicitly supports macOS and Windows and requires uv.
metadata:
  author: "harry0703@hotmail.com"
  upstream_version: "1.3.2"
  upstream: "https://github.com/harry0703/MoneyPrinterTurbo"
  upstream_commit: "ad5496f1b729d1d7e361dd972015d26c08b0e052"
  local_wrapper_version: "1.2.0"
  language: en-US
---

# MoneyPrinterTurbo Video Generation

The user may provide only a topic or script. The agent should install or reuse the pinned environment, generate the video, wait for the foreground task to finish, and deliver the final MP4. Do not stop at installation instructions when generation can proceed.

The local `mpt_agent.py` wrapper locks two things:

1. the reviewed upstream helper script, verified by Git blob SHA;
2. the pinned MoneyPrinterTurbo checkout under `tools/web-media/apps/MoneyPrinterTurbo`, preventing fallback to a moving `main.zip`.

If the pinned project is missing, the wrapper may invoke `scripts/install_web_media_stack.py --profile creator`. Do not bypass integrity checks or redirect the wrapper to an unreviewed root.

## Required behavior

1. Ask the user for API credentials only when required credentials are missing, rejected, or unavailable. Combine all missing credentials into one request.
2. Do not repeatedly ask whether to continue during a normal generation task and do not return only a list of setup commands.
3. Use one foreground command for installation and generation. Allow at least 20 minutes for terminal execution.
4. Do not poll with `sleep`, `ps`, repeated `ls`, or repeated log reads. If the terminal exposes a recoverable running session, continue waiting on that same session.
5. Never print API keys, tokens, a complete `config.toml`, or credential-bearing configuration fragments.
6. On success, rely on the helper's `MPT_RESULT` and `VIDEO_FILE`. On failure, use only the reported short error or the requested log tail.

## Default video

Unless the user specifies otherwise, create a vertical `9:16` English-language video with:

- appropriately licensed stock footage, using Pexels when configured;
- an English Edge TTS voice;
- automatic subtitles;
- background music;
- the pinned project at `tools/web-media/apps/MoneyPrinterTurbo`.

User-specified language, aspect ratio, duration, style, platform, narration, and media requirements take precedence.

## Execute

Run from this Skill directory:

```bash
uv run --no-project --python 3.11 python mpt_agent.py --subject "<video topic>"
```

Do not run an extra `uv --version` probe first. If the terminal explicitly reports that `uv` is unavailable, install uv using the current official method and retry once.

The upstream official Skill defines macOS and Windows as its standard execution environments. Linux can use this repository's pinned installer and MoneyPrinterTurbo CLI, but do not claim the full upstream Agent Skill workflow is verified on Linux unless an actual run succeeds.

## Additional generation arguments

Place additional MoneyPrinterTurbo arguments after `--`, for example:

```bash
uv run --no-project --python 3.11 python mpt_agent.py \
  --subject "How space-based solar power works" \
  -- \
  --video-aspect portrait
```

If an unfamiliar argument is needed, run the pinned project's `cli.py --help` once rather than guessing an option name.

## Return-code handling

### Return code 0: deliver the video

Successful output includes fields such as:

```text
MPT_RESULT=completed
VIDEO_FILE=<absolute-path>/final-1.mp4
TASK_DIR=<absolute-path>/storage/tasks/<task_id>
LOG_FILE=<absolute-path>/run-<task_id>.log
RESULT_FILE=<absolute-path>/latest-result.json
```

The helper emits `VIDEO_FILE` only after confirming that the MP4 exists and is non-empty. Do not run redundant `ls` or `stat` checks.

If the terminal exits with code 0 but output truncation hides `MPT_RESULT`, read exactly once:

```text
<repository>/tools/web-media/apps/MoneyPrinterTurbo/.agent-logs/moneyprinterturbo-video/latest-result.json
```

`status=completed` indicates success.

### Return code 10: request missing input once

The helper emits `MPT_NEEDS_INPUT` with the fields that are actually missing. Ask only for those fields. Possible environment variables include:

```text
MPT_LLM_PROVIDER
MPT_LLM_API_KEY
MPT_LLM_BASE_URL
MPT_LLM_MODEL_NAME
MPT_PEXELS_API_KEY
MPT_VOLCENGINE_ARK_API_KEY
MPT_OFOX_API_KEY
MPT_METASO_MINIMAX_API_KEY
MPT_MUAPI_API_KEY
```

If the helper returns any of the following billing-confirmation markers, explain that the corresponding service will create a billable task and obtain explicit user approval before retrying with the matching flag. Never confirm charges automatically:

- `SEEDANCE_CHARGE_CONFIRMATION_REQUIRED` → `--confirm-seedance-charge`
- `WAVESPEED_CHARGE_CONFIRMATION_REQUIRED` → `--confirm-wavespeed-charge`
- `OFOX_CHARGE_CONFIRMATION_REQUIRED` → `--confirm-ofox-charge`
- `METASO_MINIMAX_CHARGE_CONFIRMATION_REQUIRED` → `--confirm-metaso-minimax-charge`
- `MUAPI_CHARGE_CONFIRMATION_REQUIRED` → `--confirm-muapi-charge`

After the user supplies required values, pass them only as environment variables for that run and retry the original command. Do not write secrets into chat-visible command examples, logs, or Git.

### Return code 1: repair or report

Use `MPT_ERROR` and `LOG_FILE` to repair a recoverable failure and retry once. Ask for a new API key only when the failure actually requires one. If the retry fails, report the failed stage, concise error, and log path.

## Use with a research-driven media project

When the user requires research, named sources, citations, or specific user-owned media, load `../web-media-producer/SKILL.md` first:

1. create the research project and asset manifest;
2. collect openly licensed or user-authorized sources;
3. fact-check and prepare the script and shot list;
4. pass the final topic or script to this Skill for generation;
5. merge the resulting task directory and media provenance into the project deliverables.

Technical download capability does not imply reuse rights. Before publication, review media-provider terms, attribution, music rights, factual accuracy, and target-platform rules.
