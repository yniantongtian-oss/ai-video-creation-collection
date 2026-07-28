# ComfyUI 工作流包

本目录提供三套 Wan2.2 工作流。它们只使用 ComfyUI 核心节点，不要求额外安装第三方自定义节点。

## 工作流

| 文件 | 用途 | 默认输出 |
|---|---|---|
| `wan22_t2v_4step.json` | 文生视频，Wan2.2 双阶段 4-step LoRA | 81 帧，16 fps，约 5 秒 |
| `wan22_i2v_4step.json` | 参考图首帧驱动的图生视频 | 81 帧，16 fps，约 5 秒 |
| `wan22_long_video_3shot.json` | 三镜头连续续写与自动拼接 | 241 帧，16 fps，约 15.1 秒 |

长视频工作流的无损源文件保存为 `wan22_long_video_3shot.json.gz`。克隆仓库后先运行：

```bash
python scripts/materialize_workflows.py
```

脚本会生成标准的 `workflows/wan22_long_video_3shot.json`，随后即可通过 ComfyUI **Load** 导入。它不会覆盖内容不同的现有 JSON，除非显式加 `--force`。

长视频工作流不是三个互不相关的片段：第 1、2 镜头的最后一帧会分别作为下一镜头的首帧，并在最终拼接时删除第 2、3 镜头重复的边界帧。

## 环境要求

需要包含以下核心节点的较新 ComfyUI：

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

工作流默认使用 Wan2.2 14B FP8 双模型和 4-step LoRA。实际显存占用与生成速度取决于 ComfyUI 版本、offload、分辨率、帧数、系统内存和显卡，不保证某个固定显存容量一定能够运行。

节点与模型文件名在 2026-07-28 对照 ComfyUI 官方 Wan2.2 blueprints 检查，来源记录见 `models.json`。

## 一键准备模型

先查看下载计划：

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

确认路径、网络和磁盘空间后下载：

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI
```

下载脚本不会覆盖同名文件；只有使用 `--force` 才会重新下载。模型权重体积很大，运行前应核对上游条款和剩余磁盘空间。

## 导入步骤

1. 克隆或下载本仓库。
2. 运行 `python scripts/materialize_workflows.py` 展开长视频工作流。
3. 根据 `models.json` 放置模型，或运行下载脚本。
4. 打开 ComfyUI，使用 **Load** 加载对应 JSON。
5. I2V 或长视频工作流需要参考图：放入 `ComfyUI/input/start.png`，或在 `Load Image` 节点重新上传。
6. 先保持 640×640、81 帧和默认采样设置生成最小样片。
7. 通过后再调整提示词、宽高、帧数、种子和镜头数量。

## 模型目录

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

## 参数说明

### 分辨率

默认 `640×640` 是验证规格。宽高通常保持 16 的倍数。出现 OOM 时先降分辨率或帧数，再考虑 offload、量化和其他上游支持的优化方式。

### 帧数与时长

默认 81 帧、16 fps：

```text
81 ÷ 16 ≈ 5.06 秒
```

Wan 视频潜空间通常使用符合 `4n+1` 的帧数，例如 49、65、81。调整前仍应核对当前节点与模型支持范围。

### 双阶段采样

三套工作流均采用：

- 高噪声模型：步骤 0–2，保留剩余噪声。
- 低噪声模型：步骤 2–4，不重新加噪。
- CFG：1。
- Sampler：Euler。
- Scheduler：simple。
- ModelSamplingSD3 shift：5。

不要只修改一个采样器的总步数或分界点；两阶段设置必须保持一致。

## 长视频注意事项

- 每次末帧续写都会累积主体、构图和背景漂移。
- 镜头提示词应同时写清“必须保持不变的内容”和“允许变化的动作”。
- 镜头运动方向、人物朝向和光线方向应连续。
- 三镜头模板用于验证连续生成流程，不代表一次运行就是最佳成片。
- 正式长片仍建议配合镜头表、关键帧管理、单镜头重做、剪辑、补帧、超分、音频和字幕后期。

## 校验

```bash
python scripts/materialize_workflows.py
python scripts/validate_workflows.py
python -m py_compile scripts/*.py
```

校验脚本检查 JSON、节点 ID、连接 ID、输入输出槽位、模型文件引用和必需工作流。它不能替代真实 GPU 推理测试。

## 上游与许可

- ComfyUI 代码与节点：以上游许可证为准。
- Wan2.2 代码和模型权重：以 Wan2.2 仓库、模型卡及具体权重条款为准。
- 本仓库的 MIT 许可证不自动覆盖第三方模型权重、生成素材、音乐、人物肖像或商标。
