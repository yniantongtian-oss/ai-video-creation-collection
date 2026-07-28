# AI Video Creation Collection

精选开源 AI 视频创作相关库、模型、框架与 Skill 集合（2026）。

本仓库由 Grok 协助整理，聚焦本地可部署、消费级 GPU（尤其 16GB VRAM）友好的项目，并包含自定义 Agent Skill。

## 核心模型与推理框架

| 项目 | 描述 | Stars | 链接 |
|------|------|-------|------|
| **ComfyUI** | 最强大的节点式 Diffusion 工作流前端 | 122k+ | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) |
| **Wan 2.2** | 阿里开源高质量视频生成模型（Apache 2.0） | 16k+ | [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2) |
| **LTX-Video / LTX-2** | Lightricks 实时/长视频生成，16GB 友好 | 10k+ / 8k+ | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) |
| **HunyuanVideo / 1.5** | 腾讯电影级视频模型 | 12k+ / 4k+ | [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) |
| **CogVideoX** | 清华/智谱可控视频生成 | - | [THUDM/CogVideo](https://github.com/THUDM/CogVideo) |
| **Open-Sora 2.0** | 完整开源训练+推理 Pipeline | - | [hpcaitech/Open-Sora](https://github.com/hpcaitech/Open-Sora) |

## 高级生产与 Agent 框架

| 项目 | 描述 | Stars | 链接 |
|------|------|-------|------|
| **OpenMontage** | 世界首个开源 Agentic 视频生产系统（700+ skills） | 42k+ | [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) |
| **HyperFrames** | HeyGen 开源：HTML → 视频，专为 Agent 设计 | 38k+ | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) |
| **Pixelle-Video** | AI 全自动短视频引擎（ComfyUI 集成） | 26k+ | [ATH-MaaS/Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video) |
| **MoneyPrinterTurbo** | 一键主题生成高清短视频 | 99k+ | [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) |
| **Toonflow** | 一站式 AI 短剧创作工具 | 12k+ | [HBAI-Ltd/Toonflow-app](https://github.com/HBAI-Ltd/Toonflow-app) |

## ComfyUI 专用节点与包装

- [kijai/ComfyUI-WanVideoWrapper](https://github.com/kijai/ComfyUI-WanVideoWrapper)
- [Lightricks/ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo)
- [kijai/ComfyUI-HunyuanVideoWrapper](https://github.com/kijai/ComfyUI-HunyuanVideoWrapper)
- [Comfy-Org/ComfyUI-Manager](https://github.com/Comfy-Org/ComfyUI-Manager)

## 自定义 Skill（本仓库）

见 [`skills/ai-video-creation/SKILL.md`](skills/ai-video-creation/SKILL.md)

此 Skill 专为本地 16GB VRAM 环境优化，包含模型选择决策、量化建议、长视频拼接技巧与工作流指南。可直接用于支持 Agent Skills 的 AI 编程助手。

## 使用建议

1. 优先使用 ComfyUI + LTX-2.3 distilled 或 Wan 2.2 5B/量化版作为日常驱动。
2. 追求质量时切换到 Wan 2.2 14B FP8 或 HunyuanVideo-1.5。
3. 长视频采用「短 clip + 末帧 I2V 续写 + IC-LoRA 一致性」策略。
4. 中国大陆用户可优先使用 ModelScope 镜像下载权重。

## 贡献

欢迎提交 PR 补充更多优质开源项目或更新模型版本。

---

*整理时间：2026-07-28 | 由 Grok 辅助创建*
