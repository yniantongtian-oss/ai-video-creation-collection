# AI Video Workflow Troubleshooting

Save the error log, workflow, model name, versions, and complete environment information before changing anything. Change only a small number of variables at a time.

## General troubleshooting order

1. Reproduce the smallest failing case.
2. Record OS, GPU, driver, CUDA, Python, PyTorch, and application versions.
3. Verify model, VAE, text encoder, LoRA, and custom-node paths.
4. Remove nonessential nodes, control conditions, and post-processing.
5. Test with fewer frames, lower resolution, and batch size 1.
6. Compare against the official upstream example.
7. Restore custom content only after the official example works.

## CUDA OOM / insufficient VRAM

### Common causes

- Frame count, resolution, or batch size is too high.
- Multiple models, VAEs, text encoders, and control networks remain resident at once.
- Precision or quantization does not match the hardware.
- Custom nodes retain intermediate tensors or caches.
- Other processes are consuming GPU memory.

### Recommended order

1. Close other GPU processes and restart the workflow.
2. Set batch size to 1.
3. Reduce frame count, then dimensions.
4. Disable optional Control, LoRA, upscaling, and interpolation.
5. Use only upstream-supported low precision, quantization, tiling, or offload.
6. Verify system RAM is sufficient for CPU offload.
7. Record peak VRAM instead of tuning by intuition.

Do not generalize one successful run to all resolutions, frame counts, and workflows.

## Missing ComfyUI nodes

### Symptoms

- Red unknown nodes after loading a workflow.
- The node name exists but ports differ.
- Import errors after node installation.

### Checks

1. Identify the node repository from workflow metadata or author documentation.
2. Verify the node version or commit, not only the repository name.
3. Check whether the node was renamed, split, or merged into core.
4. Read the first real exception in the ComfyUI console.
5. Test in a clean environment with only the minimum required node set.
6. Do not execute install scripts from unknown sources automatically.

## Incorrect model or component paths

### Symptoms

- Missing checkpoint, VAE, text encoder, CLIP, or LoRA.
- A same-named but incompatible file is loaded.
- Output color, structure, or dimensions are incorrect.

### Checks

- Confirm required file type and directory from the workflow.
- Verify filename, size, hash, or model card.
- Distinguish full models, transformers, VAEs, text encoders, and quantized files.
- Check symlinks, network drives, and permissions.
- Restart the application if it caches model lists.

## dtype, CUDA, or dependency incompatibility

### Symptoms

- `not implemented for ...`, `invalid device function`, or `no kernel image`.
- Flash Attention, xFormers, or custom-kernel compilation failures.
- dtype or operator errors while loading models.

### Checks

1. Confirm the GPU architecture against upstream requirements.
2. Use the upstream-recommended Python, PyTorch, and CUDA combination.
3. Do not mix pinned versions from unrelated tutorials.
4. Disable optional acceleration libraries and validate the base pipeline.
5. Record the dependency set before reinstalling.
6. Test in an isolated environment.

## Video flicker

Possible causes include unstable frame detail, time-varying prompts or controls, frame-by-frame post-processing, or conflicting subject/camera motion.

Try shorter shots, smaller motion, stable identity/wardrobe/lighting/background anchors, separate tests for generation/upscaling/interpolation, reduced per-frame randomness, and model-supported consistency or keyframe controls.

## Character or product drift

- Move from T2V to I2V or keyframe-driven generation.
- Put invariant traits in a global anchor.
- Reuse the same reference assets and naming across shots.
- Shorten shots and connect them in editing.
- Allow only a small number of explicit changes.
- Record model, seed, and parameters for approved shots.

## Broken motion or camera jumps

- Write motion as start → process → end.
- Avoid too many complex actions in one short shot.
- Separate subject motion from camera motion.
- For continuation, inspect boundary composition, speed, and direction.
- Add intermediate keyframes or shorter clips when necessary.

## Garbled text

Video models are generally unreliable for long readable text. Generate text-free visuals and add titles, subtitles, logos, or scene text in post-production. Use a separate image asset or tracked overlay when text must appear in the scene.

## Frame-rate, duration, or encoding problems

Check generated frame count against target fps, duplicated/dropped boundary frames, interpolation output fps, audio sample rate and duration, video time base, FFmpeg arguments, and container/platform requirements.

Record:

```text
Source frames:
Source fps:
Interpolation factor:
Output fps:
Video duration:
Audio duration:
Encoder/container:
```

## Troubleshooting report template

```text
Problem:
Minimal reproduction:
First relevant error:
Environment:
Model and version:
Workflow and node versions:
Input specification:
Already tried:
Observed change:
Next single-variable test:
```
