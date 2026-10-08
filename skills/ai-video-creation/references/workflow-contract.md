# Standard Workflow Delivery Contract

An AI-video plan should be executable by another person, not just a model name and an unspecific task.

## 1. Requirements summary

```text
Project:
Goal:
Audience/platform:
Total duration:
Aspect ratio:
Target resolution and frame rate:
Generation mode: T2V / I2V / V2V / continuation / mixed
Input assets:
Visual style:
Audio and subtitles:
Hardware and environment:
Commercial-use requirements:
Explicit assumptions:
```

## 2. Technical route

```text
Primary route:
Why:
Fallback route:
Condition for switching:
Versions/weights/licenses still requiring verification:
```

Do not merely write "recommended model." Explain how the choice maps to the project constraints.

## 3. Minimal validation

Define a low-cost experiment with clear pass/fail criteria:

```text
Validation shot: S001
Duration: 2–5 seconds
Input:
Resolution:
Frame rate:
Fixed seed:
Disabled: upscaling / interpolation / unnecessary LoRA / unnecessary Control
Pass criteria:
First adjustment after failure:
```

## 4. Shot list

Recommended fields:

| Field | Meaning |
|---|---|
| shot_id | unique shot identifier |
| start_sec | timeline start |
| duration_sec | shot duration |
| mode | T2V / I2V / V2V / continuation |
| visual | scene and composition |
| action | subject motion and temporal change |
| camera | framing, position, and movement |
| input_asset | reference image, video, or keyframe |
| model | actual model and version |
| seed | reproducible seed |
| status | planned / test / approved / rejected |
| notes | issues, revisions, and approval notes |

Across shots, check identity, wardrobe, product structure, lighting direction, palette, screen direction, and motion continuity.

## 5. Visual direction sheet

### Global anchors

```text
Subject identity:
Appearance/material:
Wardrobe/product color:
Environment/period:
Art direction:
Color and lighting:
Lens/camera character:
```

### Shot-level specification

```text
[Subject] performs [action] in [scene].
Camera: [framing/position], moving with [camera motion].
Lighting: [lighting]. Overall style: [style].
Keep [invariant elements] stable from start to end; allow only [permitted changes].
```

### Negative constraints

Use defect-specific constraints rather than keyword dumping:

```text
identity drift, extra limbs, structural deformation, abrupt background changes,
camera teleportation, severe flicker, unreadable text
```

## 6. Installation and execution

Installation instructions must:

- come from current official documentation;
- state OS, Python, and PyTorch/CUDA prerequisites;
- avoid mixing dependency pins from unrelated tutorials;
- point model downloads to official repositories, official model pages, or upstream-recommended mirrors;
- label community quantizations, nodes, and workflows as third-party;
- read secrets from environment variables instead of committing them.

When a version cannot be verified, use a placeholder or tell the user to check upstream rather than inventing one.

## 7. Reproducibility record

Record at least:

```json
{
  "model": "",
  "model_revision": "",
  "workflow": "",
  "custom_nodes": [],
  "seed": null,
  "width": null,
  "height": null,
  "fps": null,
  "frames": null,
  "prompt": "",
  "negative_prompt": "",
  "input_assets": [],
  "post_processing": []
}
```

## 8. Quality control

### Visual

- Identity, product structure, and wardrobe remain stable.
- Hands, faces, text, logos, and edges are acceptable.
- No unacceptable flicker, ghosting, stretching, interpenetration, or background jumps.
- Camera motion is smooth and does not abruptly accelerate or teleport.

### Temporal

- Actions have a beginning, transition, and end.
- Shot continuity respects direction, eyelines, and spatial relationships.
- Total duration, shot duration, and pacing match the script.

### Audio

- Narration, music, ambience, and lip sync align appropriately.
- No clipping, excessive noise, abrupt audio changes, or unreviewed rights risks.

### Delivery

- Aspect ratio, resolution, frame rate, codec, and file format are correct.
- Subtitles avoid conflicts with platform UI safe areas.
- Project files, visual direction records, seeds, and license records are preserved.

## 9. Fallbacks

Every plan should include at least one fallback, for example:

- unstable T2V subject → create a keyframe and switch to I2V;
- long-shot drift → split into shorter clips and edit them together;
- insufficient VRAM → reduce frames/resolution/batch, then use upstream-supported offload or quantization;
- ComfyUI node conflicts → validate in a clean environment with only the minimum node set;
- generated text is unreadable → add text in post-production instead of asking the video model to render it.

## 10. Response boundary

Only say a video or file was generated after an actual tool or runtime confirms success. If only planning was completed, describe it as a production plan, pending workflow, or project scaffold.
