# Contributing

Thanks for contributing AI video models, frameworks, tools, workflows, and Skills. The goal of this repository is to remain **trustworthy, executable, and maintainable**, not to maximize the number of entries.

## Inclusion criteria

Prefer:

- Official model or framework repositories.
- Projects with clear documentation, licensing, and maintenance history.
- Tools that add a distinct capability rather than merely repackage an existing one.
- Projects with clear value for local workflows, research, training, batch processing, or Agent Skills.

Use caution or exclude:

- Repositories with no license, unclear provenance, or binary-only releases.
- Projects promoted through unverifiable performance claims or artificial popularity signals.
- Model mirrors whose weight provenance cannot be verified.
- Projects containing plaintext secrets, malicious installers, or high-risk dependencies.
- Unmaintained projects when a reliable replacement already exists.

## Editing the project catalog

Edit `catalog/projects.json`. Every entry must contain:

```json
{
  "id": "lowercase-kebab-case",
  "name": "Project Name",
  "category": "video-model",
  "repository": "https://github.com/owner/repository",
  "official": true,
  "license": "See upstream LICENSE and model terms",
  "capabilities": ["text-to-video"],
  "when_to_use": "Explain when this project is appropriate.",
  "notes": "Describe limitations and verification requirements."
}
```

Allowed categories are defined by `ALLOWED_CATEGORIES` in `scripts/validate_catalog.py`. If you add a category, document the reason and update the validator in the same change.

## Description rules

- Do not include star counts.
- Avoid claims such as "best", "number one", or "guaranteed to run" that cannot be maintained over time.
- Describe VRAM, speed, resolution, and duration as environment-dependent and provide a way to verify them.
- Distinguish official projects, community nodes, community quantizations, and third-party workflows.
- If licensing is uncertain, write `See upstream LICENSE and model terms` instead of guessing.
- Point URLs at repository roots rather than search results, branch pages, or download redirects.

## Editing ComfyUI workflows

Workflows live in `workflows/`. Changes must follow these rules:

- Prefer ComfyUI core nodes. If a third-party node is required, record its repository, version, and installation method.
- Keep model filenames, directories, and download sources synchronized with `workflows/models.json`.
- Do not present structural validation as proof of successful real GPU inference.
- When changing sampling steps, also check the high-noise/low-noise boundary, noise injection, and leftover-noise settings.
- When changing frame counts, fps, or stitching behavior, update the default duration documented in `workflows/README.md`.
- The canonical three-shot workflow JSON is generated from a compressed source. Update `wan22_long_video_3shot.json.gz` as needed and verify the expanded JSON.
- Do not commit model weights, generated video, personal media, or secrets.

Workflow validation must verify:

- Unique node IDs and link IDs.
- Existing source nodes, target nodes, and slots for every link.
- Consistent reverse references between node inputs/outputs and link IDs.
- Correct `last_node_id`, `last_link_id`, and workflow version.
- Presence of `CreateVideo`, `SaveVideo`, and task-required nodes.
- Every referenced model appears in `models.json`.

## Editing Skills

Keep `skills/ai-video-creation/SKILL.md` focused:

- Put trigger conditions, decision flow, execution rules, and output requirements in the main Skill.
- Put detailed tables, long explanations, and troubleshooting material in `references/`.
- Put reusable templates in `templates/`.
- Do not turn the main Skill into a list of currently popular projects.
- Do not claim that an Agent has local GPU access, video-generation software, or background execution unless it actually does.

## Local checks

Run before submitting:

```bash
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python -m py_compile scripts/*.py

# Optional: create a temporary project to verify the scaffolding
python scripts/scaffold_project.py \
  --name "ci-smoke-test" \
  --output /tmp/ai-video-creation-test \
  --duration 7 \
  --shot-length 3 \
  --aspect-ratio 16:9 \
  --mode mixed
```

Delete the temporary directory after inspection.

## Pull request requirements

A PR description should include:

- The purpose of the change.
- Projects, workflows, or model references added or removed.
- Official sources and license-verification results.
- Checks that were run and their results.
- Whether real GPU inference was performed; say explicitly when it was not.
- Remaining uncertainties or follow-up work.

Keep each PR focused on one topic whenever possible. Avoid mixing catalog updates, Skill rewrites, and unrelated formatting changes.
