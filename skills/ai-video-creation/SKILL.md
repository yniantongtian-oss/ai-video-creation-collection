---
name: ai-video-creation
description: Handle local open-source AI video generation and creation workflows using ComfyUI and models like LTX-Video, Wan 2.2, HunyuanVideo, CogVideoX, Mochi. Trigger on requests for AI video creation, text-to-video, image-to-video, long video extension, ComfyUI video pipelines, VRAM optimization for 16GB GPUs, model recommendations, or open-source video gen libraries. Focus on practical local setups, quantization, splicing, and scalable production.
---

# AI Video Creation

## Overview

Specialize in open-source AI video generation pipelines optimized for consumer GPUs (especially 16GB VRAM like RTX 5060). Cover model selection, ComfyUI workflows, quantization (GGUF/FP8/Q4/Q5), long-form extension/splicing techniques, and production scaling.

## Core Stack (2026 Recommended)

Prioritize these for local use:

1. **ComfyUI** (mandatory frontend)
   - Repo: https://github.com/comfyanonymous/ComfyUI
   - Use ComfyUI Manager for custom nodes.
   - Video tools: native CreateVideo / LoadVideo / VideoSlice nodes + community packs.

2. **LTX-Video / LTX 2.3 / LTX Director 2.0** (Lightricks) — best for speed + 16GB VRAM
   - Official: https://github.com/Lightricks/LTX-Video
   - ComfyUI nodes: https://github.com/Lightricks/ComfyUI-LTXVideo
   - Strengths: Real-time capable, native audio in later versions, long clips (up to 30-60s with extension), IC-LoRA for consistency, Retake Mode.
   - VRAM: 2B distilled ~8-12GB, 13B/22B with FP8/quant ~16GB usable.
   - Desktop app alternative: LTX-Desktop.

3. **Wan 2.2** (Alibaba) — highest open quality + fully Apache 2.0
   - Repo: https://github.com/Wan-Video/Wan2.2
   - Models: T2V-A14B, I2V-A14B, TI2V-5B (efficient hybrid).
   - ComfyUI: Kijai conversions + native nodes preferred. GGUF versions (City96) for lower VRAM.
   - Strengths: Strong motion, faces, multilingual (excellent Chinese), MoE architecture.
   - Note: Later Wan 2.5+ are closed/API-only. Stick to 2.2 for open weights.

4. **HunyuanVideo / HunyuanVideo-1.5** (Tencent)
   - Original: https://github.com/Tencent-Hunyuan/HunyuanVideo
   - 1.5 (lighter 8.3B): https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
   - ComfyUI wrappers by Kijai and official.
   - Strengths: Cinematic quality, motion coherence. 1.5 much more accessible on consumer GPUs with distillation/FP8.
   - License: Tencent Community (check commercial restrictions, especially EU/UK).

5. **CogVideoX** (THUDM)
   - https://github.com/THUDM/CogVideo
   - Good prompt adherence, 2B/5B variants, Diffusers + ComfyUI support.
   - Solid for longer controllable clips (6-10s).

6. **Mochi 1** (Genmo)
   - Apache 2.0, strong fluid motion. Good alternative when motion quality is priority.

7. **Open-Sora 2.0**
   - https://github.com/hpcaitech/Open-Sora
   - Full open pipeline (data, train, infer). Best for research or custom training. Quality closer to Hunyuan/Wan.

## VRAM Optimization for 16GB (RTX 5060 class)

- Prefer FP8 / GGUF Q4_K_M / Q5 quantized checkpoints.
- Use TeaCache, sequential offloading, or xDiT parallelism where available.
- LTX distilled + Wan 5B / CogVideoX 2B as daily drivers.
- For 14B models: enable model CPU offload + attention slicing.
- Upscale last with Upscayl or ComfyUI ESRGAN/RealESRGAN nodes instead of generating at high res.

## Long Video / Extension Techniques

- Autoregressive / sliding window: LTX long multi-prompt workflows, Wan video continuation.
- Splicing: Generate short clips → use last frame as I2V start for next segment. Match seed/motion strength carefully.
- IC-LoRA / subject consistency LoRAs to prevent character drift.
- Audio: Prefer models with native audio (LTX 2.x) or post-process with separate TTS + sync.
- For production scale: Look at SeedCamp-style orchestration (tiered routing, batch, cost tracking) or UniVA multi-agent framework.

## Additional Useful Open Projects

- HyperFrames (HeyGen): Agent-native HTML-to-video / motion graphics. Great for structured production.
- UniVA: Open multi-agent video generalist (understanding + edit + gen).
- OpenMontage / OpenDirector: Higher-level agentic video studios.
- Diffusers library: Always useful for scripting outside ComfyUI.
- Awesome lists: showlab/Awesome-Video-Diffusion, sjtuplayer/Awesome-Video-Foundations.

## Workflow Guidelines

When helping with a video task:
1. Confirm hardware (VRAM) and target length/resolution/quality.
2. Recommend primary model + ComfyUI workflow JSON if available.
3. Provide exact download paths (Hugging Face preferred, ModelScope for CN users).
4. Include quantization advice and common error fixes (missing nodes, OOM, VAE mismatch).
5. For multi-shot or long form: Suggest storyboard → keyframe → I2V chaining approach.
6. Always note license implications for commercial use.

## References

Place detailed model cards, example workflow JSONs, and quantization tables in references/ as needed.
Keep this SKILL.md focused on decision-making and current best practices.
