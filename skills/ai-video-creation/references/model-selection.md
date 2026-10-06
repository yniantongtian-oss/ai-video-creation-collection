# Model and Workflow Selection

Use this document to choose candidate technical routes. It does not replace upstream README files, model cards, or licenses. Re-verify exact versions, weights, quantizations, and hardware requirements before execution.

## Classify the task first

| Task | Confirm first | Common routes |
|---|---|---|
| Text-to-video | visual control, motion, shot length, text rendering | Wan2.2, LTX, HunyuanVideo, CogVideo |
| Image-to-video | reference quality, features that must remain stable, camera motion | current official I2V models or ComfyUI workflows |
| Video-to-video | whether to preserve motion, composition, identity, duration, and audio | V2V or controlled pipelines |
| Continuation | boundary continuity, drift tolerance, accumulated error | native extension or shot-based generation plus editing |
| Multi-shot short | script, shot list, character design, sound, subtitles | multiple models plus editing |
| Research/training | data, compute, distributed setup, evaluation | Open-Sora, Diffusers, or official training code |
| Services/batch | API, queues, caching, retries, logs | Diffusers scripts or ComfyUI API |

## Candidate routes

### ComfyUI

Use when you need node-based construction, reusable workflows, debugging, model/control/LoRA/post-processing composition, or API execution of a validated workflow.

Verify the ComfyUI version, required custom nodes and versions, model/VAE/text-encoder/LoRA paths, and custom-node source and license.

### Wan2.2

Use when official Wan T2V, I2V, or related published capabilities fit the task.

Verify the current official model/task list, weight license and input requirements, and the current inference or ComfyUI integration path.

### LTX-Video / LTX-2

Use when current upstream video generation, keyframe, extension, or audio-video features are needed.

Verify the currently recommended model/documentation, whether the required feature belongs to the selected model, and its dependencies, precision, and hardware requirements.

### HunyuanVideo / HunyuanVideo-1.5

Use when the official HunyuanVideo ecosystem fits the project or when comparing the base and lighter routes.

Verify which repository/version is in use, code and weight terms, regional/commercial conditions, and supported input modes.

### CogVideo

Use for CogVideo models or Diffusers/Python pipeline integration.

Verify the exact model branch/card, resolution/frame/input requirements, dependency versions, and license.

### Open-Sora

Use for training, evaluation, research, or a custom full-generation pipeline. Do not default to it for users who only want a quick short video on ordinary hardware.

### Diffusers

Use for Python automation, batching, testing, services, or composition with schedulers, encoders, VAEs, and other model components.

Verify that the current Diffusers version contains the required pipeline and that model examples match the installed PyTorch, Transformers, and Accelerate versions.

## Hardware routing principles

Do not decide from VRAM size alone. Also check:

- parameter count, precision, and quantization;
- frame count, resolution, batch size, and number of controls;
- whether the text encoder, VAE, and multiple models remain resident simultaneously;
- system RAM, storage, PCIe transfer, and offload cost;
- GPU architecture support for dtype, Flash Attention, or required kernels.

### Conservative order

1. Choose a smaller or lower-precision route explicitly supported upstream.
2. Measure peak VRAM using a 2–5 second sample.
3. Reduce frame count and resolution before batch size.
4. Use CPU offload, tiling, or quantization only when supported.
5. Add control nodes, LoRAs, upscaling, and interpolation only after the baseline works.

## Selection record

Record at least:

```text
Task:
Primary route:
Fallback route:
Reason:
Input assets:
Target duration/aspect ratio/frame rate:
Minimal validation target:
Upstream details that still need verification:
License risks:
Fallback if validation fails:
```
