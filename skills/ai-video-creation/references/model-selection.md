# Model and Workflow Selection

Use this document to choose candidate technical routes. It does not replace upstream README files, model cards, or licenses. Re-verify exact versions, weights, quantizations, and hardware requirements before execution.

## Classify the task first

| Task | Confirm first | Common routes |
|---|---|---|
| Text-to-video | visual control, motion, shot length, text rendering | Wan2.2, Wan2.1, LTX-2, HunyuanVideo, CogVideo, Mochi, MAGI-1 |
| Image-to-video | reference quality, features that must remain stable, camera motion | Wan, LTX-2, FramePack, LongCat-Video, SkyReels-V2, or a ComfyUI workflow |
| Audio and video together | whether the selected weights actually generate audio, and which license applies | LTX-2 |
| Video-to-video | whether to preserve motion, composition, identity, duration, and audio | V2V or controlled pipelines |
| Continuation | boundary continuity, drift tolerance, accumulated error | MAGI-1, FramePack, LongCat-Video, or shot-based generation plus editing |
| Multi-shot short | script, shot list, character design, sound, subtitles | multiple models plus editing |
| Research/training | data, compute, distributed setup, evaluation | Open-Sora, Diffusers, Mochi fine-tuning, or official training code |
| Services/batch | API, queues, caching, retries, logs | Diffusers scripts or ComfyUI API |

## Candidate routes

### ComfyUI

Use when you need node-based construction, reusable workflows, debugging, model/control/LoRA/post-processing composition, or API execution of a validated workflow.

Verify the ComfyUI version, required custom nodes and versions, model/VAE/text-encoder/LoRA paths, and custom-node source and license.

### Wan2.2 and Wan2.1

Use Wan2.2 when its official T2V, I2V, or other published task fits. Use Wan2.1 when its separate checkpoints, including the consumer-GPU and text-rendering routes, fit better.

Verify the repository, checkpoint, weight license, and hardware on a short sample. Do not treat Wan2.1 and Wan2.2 as interchangeable files.

### LTX-Video

Use the Apache-2.0 LTX-Video repository for the earlier LTX-Video line, including keyframes and extension documented there.

### LTX-2

Use `Lightricks/LTX-2` when the shot needs official audio-video generation, the Python inference package, or the upstream LoRA trainer.

LTX-2 and later LTX-2.x weights use community licenses that differ by release line. Read the license that matches the weights. This is not the Apache-2.0 LTX-Video repository.

### HunyuanVideo / HunyuanVideo-1.5

Use when the official HunyuanVideo ecosystem fits the project or when the lighter 1.5 route is the one you intend to run.

The HunyuanVideo-1.5 community license does not apply in the European Union, the United Kingdom, or South Korea. Confirm the repository, weight terms, and supported input modes before use.

### CogVideo

Use for CogVideo models or Diffusers/Python pipeline integration.

Verify the exact model branch/card, resolution/frame/input requirements, dependency versions, and license. The repository code is Apache-2.0; model weights may use different terms.

### FramePack

Use for progressive next-frame generation when a one-shot sampler is a poor fit for the clip length. The upstream design keeps the packed context at a constant length as the clip grows. Measure memory locally.

### Mochi

Use when an Apache-2.0 text-to-video checkpoint with an official fine-tuning path is the right base. Confirm that the trainer and the weights belong together.

### MAGI-1

Use for official autoregressive generation or continuation. Confirm context length and weight terms on a short sample.

### LongCat-Video and SkyReels-V2

Use LongCat-Video when its official long-clip checkpoints and MIT code license fit. Use SkyReels-V2 when its official longer film-style checkpoints fit. SkyReels-V2 uses custom terms; read `LICENSE.txt` before commercial use. LongCat weight files can differ from the code license, and the repository also documents a separate avatar line.

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
