# ComfyUI Workflow Pack

This directory provides three Wan2.2 workflows using only ComfyUI core nodes, with no additional third-party custom nodes required.

## Workflows

| File | Purpose | Default output |
|---|---|---|
| `wan22_t2v_4step.json` | Text-to-video with the Wan2.2 two-stage 4-step LoRA route | 81 frames, 16 fps, about 5 seconds |
| `wan22_i2v_4step.json` | Image-to-video driven by a reference first frame | 81 frames, 16 fps, about 5 seconds |
| `wan22_long_video_3shot.json` | Three-shot continuation with automatic assembly | 241 frames, 16 fps, about 15.1 seconds |

The lossless source for the long workflow is stored as `wan22_long_video_3shot.json.gz`. After cloning, run:

```bash
python scripts/materialize_workflows.py
```

This creates `workflows/wan22_long_video_3shot.json` for import through ComfyUI **Load**. It will not overwrite a different existing JSON unless `--force` is supplied.

The long workflow is not three unrelated clips: the final frame of shots 1 and 2 becomes the first frame of the next shot, and duplicate boundary frames are removed during final assembly.

## Environment requirements

Use a recent ComfyUI build that provides:

- `UNETLoader`
- `CLIPLoader`
- `VAELoader`
- `LoraLoaderModelOnly`
- `ModelSamplingSD3`
- `KSamplerAdvanced`
- `WanImageToVideo`
- `CreateVideo`
- `SaveVideo`
- `ImageFromBatch`
- `ImageBatch`

The workflows use Wan2.2 14B FP8 dual models and 4-step LoRAs by default. Actual VRAM use and speed depend on the ComfyUI version, offload strategy, resolution, frame count, system RAM, and GPU. No fixed VRAM capacity is guaranteed.

Node and model filenames were checked against official ComfyUI Wan2.2 blueprints on 2026-07-28. Provenance is recorded in `models.json`.

## Prepare models

Preview the download plan:

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

After checking paths, connectivity, and disk space:

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI
```

The downloader does not overwrite files with the same name unless `--force` is used. Model weights are large; review upstream terms and available disk space first.

## Import

1. Clone or download the repository.
2. Run `python scripts/materialize_workflows.py`.
3. Place models according to `models.json`, or use the downloader.
4. Open ComfyUI and load the relevant JSON with **Load**.
5. I2V and long-video workflows need a reference image at `ComfyUI/input/start.png`, or upload another image in the Load Image node.
6. Keep the initial test at 640×640, 81 frames, and default sampling settings.
7. After validation, adjust prompts, dimensions, frame count, seed, and shot count.

## Model directories

```text
ComfyUI/
└── models/
    ├── diffusion_models/
    │   ├── wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors
    │   ├── wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors
    │   ├── wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors
    │   └── wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors
    ├── loras/
    │   ├── wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors
    │   ├── wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors
    │   ├── wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors
    │   └── wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors
    ├── text_encoders/
    │   └── umt5_xxl_fp8_e4m3fn_scaled.safetensors
    └── vae/
        └── wan_2.1_vae.safetensors
```

## Parameters

### Resolution

`640×640` is a validation target. Keep width and height on supported multiples, typically 16. On OOM, reduce resolution or frame count before trying offload, quantization, or other upstream-supported optimizations.

### Frame count and duration

At 81 frames and 16 fps:

```text
81 / 16 ≈ 5.06 seconds
```

Wan latent video commonly uses frame counts compatible with `4n+1`, such as 49, 65, or 81. Verify the current model and node limits before changing them.

### Two-stage sampling

All three workflows use:

- high-noise model: steps 0–2, keep remaining noise;
- low-noise model: steps 2–4, do not add fresh noise;
- CFG: 1;
- sampler: Euler;
- scheduler: simple;
- ModelSamplingSD3 shift: 5.

Do not change only one sampler's total steps or boundary; keep the two stages consistent.

## Long-video notes

- Final-frame continuation accumulates subject, composition, and background drift.
- Prompts should state what must remain fixed and what motion may change.
- Camera direction, subject orientation, and lighting direction should remain coherent across shots.
- The three-shot template validates the continuation pipeline; it is not automatically an optimal final edit.
- Longer productions should still use shot planning, keyframe management, per-shot reruns, editing, interpolation, upscaling, audio, and subtitle post-production.

## Validation

```bash
python scripts/materialize_workflows.py
python scripts/validate_workflows.py
python -m py_compile scripts/*.py
```

Validation checks JSON, node IDs, link IDs, slots, model references, and required workflows. It does not replace real GPU inference.

## Upstream and licensing

- ComfyUI code and nodes: follow upstream licenses.
- Wan2.2 code and model weights: follow the Wan2.2 repository, model cards, and weight-specific terms.
- This repository's MIT license does not automatically cover third-party model weights, generated media, music, likeness rights, or trademarks.
