# Local Setup

This repository does not include model weights and does not require a specific generation framework. Catalog validation and project scaffolding depend only on the Python standard library.

## 1. Clone the repository

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection
```

Python 3.10 or newer is recommended.

## 2. Validate the project catalog

```bash
python scripts/validate_catalog.py
```

Expected output is similar to:

```text
Catalog OK: 10 projects, 10 unique repositories.
```

## 3. Create a video project

```bash
python scripts/scaffold_project.py \
  --name "city-night-promo" \
  --duration 20 \
  --shot-length 4 \
  --aspect-ratio 9:16 \
  --fps 24 \
  --mode mixed
```

Available arguments:

| Argument | Description |
|---|---|
| `--name` | Required project name |
| `--output` | Parent output directory, default: `projects` |
| `--duration` | Total duration in seconds, default: 15 |
| `--shot-length` | Planned shot length in seconds, default: 5 |
| `--aspect-ratio` | Frame ratio such as `16:9` or `9:16` |
| `--fps` | Target frame rate, default: 24 |
| `--mode` | `t2v`, `i2v`, `v2v`, `continuation`, or `mixed` |
| `--model` | Optional candidate model name |
| `--force` | Delete and recreate an existing project directory with the same name; use carefully |

Generated files include:

- `brief.md`: requirements, technical environment, acceptance criteria, and risks.
- `shots.csv`: a shot list automatically split by planned shot duration.
- `visual-direction.md`: global anchors, negative constraints, and shot specifications.
- `manifest.json`: project specification and reproducibility metadata.

## 4. Install the Agent Skill

Skill directory:

```text
skills/ai-video-creation
```

In tools that support directory-based Agent Skills, install this directory using that tool's current official instructions.

Example request after loading the Skill:

```text
Create an AI-video production plan for a 30-second 9:16 product promo.
I have six product images and a local ComfyUI setup with 16 GB of VRAM.
Start with a shot list, candidate models, a minimal validation plan, and a visual direction sheet.
Do not assume that video has already been generated.
```

## 5. Connect ComfyUI

This repository does not pin a fixed ComfyUI, model, or custom-node version. Recommended process:

1. Install ComfyUI from the official repository or official release path.
2. Start with a clean environment.
3. Select the target model's official instructions or a verified workflow.
4. Install only the minimum custom-node set required by that workflow.
5. Validate the model, VAE, text encoder, nodes, and VRAM requirements with a 2–5 second sample.
6. Save the validated workflow JSON and record versions and node information in `manifest.json`.

## 6. Connect Diffusers

For Python automation, batch processing, or service deployment:

1. Check current Diffusers documentation for support of the target model.
2. Create an isolated virtual environment per project.
3. Install dependencies using the target pipeline's official example.
4. Pin reproducible versions and save the dependency list.
5. Never commit API keys, access tokens, or private model URLs.

## 7. Recommended directory structure

A generated project can use:

```text
my-video-project/
├── assets/
│   ├── audio/
│   ├── images/
│   └── video/
├── outputs/
│   ├── previews/
│   └── final/
├── workflows/
├── brief.md
├── manifest.json
├── visual-direction.md
└── shots.csv
```

Do not commit large model files, caches, or rendered videos directly to this repository. Use Git LFS, object storage, or a local project directory and record source and hash information.

## 8. Security and rights

- Never commit secrets, cookies, access tokens, or signed download URLs.
- Do not use faces, voices, music, trademarks, or private media without authorization.
- Check licenses separately for third-party models, weights, nodes, and generated outputs.
- Review community workflows and custom-node code before execution.
