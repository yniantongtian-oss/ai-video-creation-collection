---
name: ai-video-creation
description: Convert AI video creation requests into executable local or open-source workflows. Use for text-to-video, image-to-video, video-to-video, continuation, multi-shot production, character consistency, ComfyUI workflows, model selection, VRAM optimization, shot lists, visual instruction packs, and troubleshooting. First establish the task, source assets, delivery specification, hardware, and licensing requirements. Prefer the repository's validated Wan2.2 and ComfyUI workflows when appropriate. Never invent model versions, repositories, nodes, VRAM usage, generation speed, or commercial-use terms.
metadata:
  version: 1.1.0
  language: en-US
---

# AI Video Creation Skill

Turn a creative request into an **executable, reproducible, and reviewable** AI-video production plan. Prefer official upstream repositories, the user's existing environment, and validated workflows in this repository. Mark unknowns for verification instead of guessing.

## Scope

Use this Skill for:

- text-to-video (T2V), image-to-video (I2V), and video-to-video (V2V);
- continuation, first/last-frame control, keyframe-driven generation, and character/product consistency;
- multi-shot shorts, ads, narrative clips, explainers, and social video;
- ComfyUI workflows, Diffusers scripts, local deployment, and VRAM optimization;
- recommendations for models, open-source libraries, nodes, workflows, or technical approaches;
- troubleshooting OOM, missing nodes, model paths, VAE, dtype, frame rate, flicker, drift, and related failures.

Do not use this Skill for unauthorized impersonation, deceptive deepfakes, illegal content, or bypassing platform safeguards.

## Working principles

1. **Define the deliverable before choosing a model.**
2. **Prefer official sources.** Verify versions, installation commands, and licenses against current upstream documentation.
3. **Reuse validated workflows.** Do not rebuild a graph that already exists and passes structural validation.
4. **Do not present estimates as facts.** VRAM, speed, maximum duration, and resolution depend on the model, quantization, nodes, drivers, and workflow.
5. **Validate small first.** Generate a 2–5 second lower-resolution sample before scaling.
6. **Split long-form work into shots.** Prefer shot lists, keyframes, short generated clips, editing, and audio post-production over one-shot generation.
7. **Keep the workflow reproducible.** Record model, workflow version, seed, resolution, frame rate, visual instructions, inputs, and post-processing.
8. **Review commercial-use terms first.** Repository, code, model-weight, and output-use terms may differ.

## Step 1: Build the production brief

Reuse information the user already provided. Determine at minimum:

- `goal`: purpose and core message;
- `mode`: T2V, I2V, V2V, continuation, character animation, or mixed;
- `duration`: total length and expected shot length;
- `aspect_ratio`: such as 16:9, 9:16, or 1:1;
- `resolution` and `fps`: target values, or a smaller validation target;
- `assets`: reference images, first/last frames, character sheets, product shots, existing video, audio, and subtitles;
- `style`: realistic, animated, cinematic, commercial, documentary, and so on;
- `hardware`: GPU, VRAM, RAM, operating system, CUDA/PyTorch environment;
- `delivery`: final format, target platform, deadline, and commercial-use requirements.

If minor information is missing but work can safely proceed, state explicit assumptions instead of blocking the plan.

## Step 2: Route the task

### T2V

Best for concept shots, environments, abstract visuals, and scenes without strict subject consistency. Write shot-level visual instructions before choosing the model.

### I2V

Best for people, products, posters, character designs, and fixed compositions. Record reference quality, desired subject motion, camera motion, and elements that must remain unchanged.

### V2V

Best for stylization, redraws, motion preservation, or enhancement of existing footage. Determine whether composition, motion, identity, duration, and audio must be retained.

### Multi-shot or long-form work

Default process:

```text
Creative goal → script/narration → shot list → keyframes → per-shot generation → consistency review
→ interpolation/upscaling → edit → narration/music/subtitles → final QC
```

Do not rely on indefinite last-frame continuation as the only strategy; composition drift, subject drift, and quality degradation can accumulate.

## Step 3: Choose the technical route

Read [`references/model-selection.md`](references/model-selection.md) and `catalog/projects.json` first.

Typical candidates include:

- **ComfyUI** for node-based debugging, reusable workflows, graphical control, or API integration.
- **Wan2.2** for supported upstream T2V, I2V, or related tasks.
- **LTX-Video / LTX-2** for current upstream keyframe, extension, or audio-video capabilities.
- **HunyuanVideo / HunyuanVideo-1.5** when that ecosystem is appropriate.
- **CogVideo** for CogVideo models or Diffusers integration.
- **Open-Sora** for research, training, or custom full-generation pipelines.
- **Diffusers** for Python automation, batching, services, or composition with other model components.

The selection must include a primary route, fallback route, rationale, known limitations, versions/licenses that still require verification, and a minimal validation configuration.

## Step 4: Reuse repository workflows

For **ComfyUI + Wan2.2**, prefer:

| Task | Workflow |
|---|---|
| Text-to-video | `../../workflows/wan22_t2v_4step.json` |
| Image-to-video | `../../workflows/wan22_i2v_4step.json` |
| Three-shot continuous video | `../../workflows/wan22_long_video_3shot.json` |

Execution order:

1. Read `../../workflows/README.md`.
2. Run `python scripts/materialize_workflows.py`.
3. Run `python scripts/validate_workflows.py`.
4. Check required files and directories in `../../workflows/models.json`.
5. Use `scripts/download_workflow_models.py --dry-run` before downloading.
6. Put user assets, visual instructions, aspect ratio, resolution, frame count, and seed into a copy rather than modifying the baseline template.
7. Validate one minimal shot before the three-shot workflow.

The three-shot template uses the final frame of one shot as the next shot's first frame and removes duplicate boundary frames during assembly. Identity, composition, and background drift can still accumulate, so do not present it as "infinite drift-free video."

**Validation boundary:** repository checks validate JSON structure, nodes, slots, links, and model references. Unless actual GPU inference succeeds, say only that structural validation passed.

## Step 5: Generate a project scaffold

When repository scripts are available:

```bash
python scripts/scaffold_project.py \
  --name "project-name" \
  --duration 30 \
  --aspect-ratio 16:9 \
  --mode mixed
```

Then complete:

- `brief.md`: goals, audience, style, constraints, and acceptance criteria;
- `shots.csv`: duration, visual content, motion, inputs, model, seed, and status per shot;
- `visual-direction.md`: visual direction, negative constraints, identity anchors, and per-shot visual instructions;
- `manifest.json`: project parameters and reproducibility information.

## Step 6: Output the plan

Present the final plan in this order:

1. Requirements summary and assumptions.
2. Primary route and fallback route.
3. Existing repository workflow or reason a new one is needed.
4. Minimal validation steps.
5. Installation and model preparation using verified official documentation.
6. Shot list.
7. Visual direction.
8. Workflow parameters: resolution, fps, frame count, seed, sampling, and post-processing.
9. Quality control for identity, hands/text, motion continuity, flicker, edges, AV sync, and subtitles.
10. Risks, licensing, and fallback behavior.

See [`references/workflow-contract.md`](references/workflow-contract.md) for the full output contract.

## Minimal validation rules

For the first run:

- 2–5 seconds;
- low or medium resolution;
- fixed seed;
- one reference image or one motion objective;
- disable nonessential upscaling, interpolation, and complex post-processing.

Scale resolution, duration, control conditions, and batch size only after the minimal test passes. Change only a few variables at a time.

## VRAM and performance

When VRAM is insufficient or performance is too slow:

1. Reduce frame count, resolution, or batch size.
2. Use upstream-supported low-precision, quantization, or tiling options.
3. Enable CPU offload only when the current pipeline supports it.
4. Reduce simultaneously loaded models, control modules, LoRAs, and custom nodes.
5. Generate at lower resolution first, then upscale/interpolate/encode.
6. Record peak VRAM, runtime, and visual-quality changes before and after adjustments.

Do not infer guaranteed compatibility from GPU memory capacity alone.

## Troubleshooting

Read [`references/troubleshooting.md`](references/troubleshooting.md) for:

- CUDA OOM or system-memory exhaustion;
- missing ComfyUI nodes or incompatible workflow versions;
- incorrect model, VAE, text-encoder, or LoRA paths;
- dtype, CUDA, PyTorch, or acceleration-library incompatibilities;
- flicker, subject drift, motion discontinuity, or image deformation;
- incorrect frame rate, duration, audio, or encoding.

## Prohibited claims and actions

- Do not invent model versions, repositories, nodes, parameters, or download URLs.
- Do not use unverified star counts as a recommendation signal.
- Do not describe community quantizations or third-party nodes as official releases.
- Do not guarantee speed, VRAM use, or maximum generation length for a specific GPU.
- Do not claim a workflow's node graph is verified without inspecting the JSON.
- Do not describe structural validation as successful GPU inference.
- Do not claim generation completed unless actual tool output confirms success.
- Do not ignore licenses, regional restrictions, or commercial-use terms for model weights.

## Related files

- [`../../workflows/README.md`](../../workflows/README.md)
- [`../../workflows/models.json`](../../workflows/models.json)
- [`references/model-selection.md`](references/model-selection.md)
- [`references/workflow-contract.md`](references/workflow-contract.md)
- [`references/troubleshooting.md`](references/troubleshooting.md)
- [`templates/video-brief.md`](templates/video-brief.md)
- [`../../catalog/projects.json`](../../catalog/projects.json)
