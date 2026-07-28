# AI Video Creation Collection

面向 **AI 视频创作、开源模型选型、本地工作流设计与 Agent Skill** 的可执行资源库。

本仓库不维护容易过期的 Stars 排名，也不把未经核验的版本、显存需求或社区项目写成确定事实。核心项目优先收录官方仓库；具体版本、模型权重、许可证和硬件要求，应在部署前再次查看上游文档。

## 这个仓库能做什么

- 用结构化目录筛选 AI 视频模型、工作流框架和基础库。
- 直接使用三套 Wan2.2 ComfyUI 工作流：文生视频、图生视频、三镜头连续长视频。
- 使用模型清单和零第三方依赖下载脚本准备工作流权重。
- 安装 `ai-video-creation` Skill，让支持 Agent Skills 的助手按照统一流程完成需求分析、模型路由、镜头拆解、提示词规划和风险检查。
- 使用项目脚手架生成 brief、镜头表、提示词包和可复现 manifest。
- 通过 GitHub Actions 自动检查资源目录、工作流结构和 Python 脚本。

## 快速开始

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection

# 展开压缩保存的三镜头工作流
python scripts/materialize_workflows.py

# 检查资源目录和三套工作流
python scripts/validate_catalog.py
python scripts/validate_workflows.py

# 创建一个 30 秒、16:9 的图生视频项目骨架
python scripts/scaffold_project.py \
  --name "产品发布短片" \
  --duration 30 \
  --aspect-ratio 16:9 \
  --mode i2v
```

项目脚手架会生成：

```text
projects/产品发布短片/
├── brief.md
├── manifest.json
├── prompts.md
└── shots.csv
```

## ComfyUI 工作流

| 工作流 | 文件 | 默认规格 | 核心逻辑 |
|---|---|---|---|
| 文生视频 | [`workflows/wan22_t2v_4step.json`](workflows/wan22_t2v_4step.json) | 81 帧、16 fps、约 5 秒 | Wan2.2 T2V 双模型、4-step 双阶段采样 |
| 图生视频 | [`workflows/wan22_i2v_4step.json`](workflows/wan22_i2v_4step.json) | 81 帧、16 fps、约 5 秒 | 参考图作为首帧，Wan2.2 I2V 双阶段采样 |
| 三镜头长视频 | `workflows/wan22_long_video_3shot.json` | 241 帧、16 fps、约 15.1 秒 | 上一镜头末帧续写，删除重复边界帧后拼接 |

三镜头工作流以无损 gzip 源文件保存。克隆后执行：

```bash
python scripts/materialize_workflows.py
```

即可生成标准 JSON。详细模型目录、导入步骤、参数说明和长视频注意事项见 [`workflows/README.md`](workflows/README.md)。

### 模型下载

先检查下载计划：

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

确认后移除 `--dry-run` 开始下载。模型文件、目标目录和官方来源记录在 [`workflows/models.json`](workflows/models.json)。

> 模型权重很大。下载和运行前应核对磁盘空间、上游模型条款以及本机 ComfyUI、PyTorch、CUDA 和驱动兼容性。

## 安装 Skill

Skill 路径：

```text
skills/ai-video-creation
```

在支持 Agent Skills 的工具中安装或加载该目录即可：

```text
安装这个目录下的 Skill：/path/to/ai-video-creation-collection/skills/ai-video-creation
```

Skill 的职责不是凭空承诺“已生成视频”，而是：

1. 把用户需求转换为明确的视频制作 brief。
2. 根据任务类型、素材、硬件和授权要求选择技术路线。
3. 在适合时复用仓库内已经校验的 ComfyUI 工作流。
4. 输出镜头表、提示词包、目录结构、执行步骤与验收标准。
5. 对显存、速度、模型版本和商业许可等不确定信息明确标注。

## 推荐起点

| 类型 | 项目 | 适合场景 | 上游 |
|---|---|---|---|
| 工作流引擎 | ComfyUI | 节点式本地工作流、API 集成、可视化调试 | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) |
| 视频模型 | Wan2.2 | 文生视频、图生视频及官方扩展能力 | [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2) |
| 视频模型 | LTX-Video / LTX-2 | 视频生成、关键帧控制、音视频能力 | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) |
| 视频模型 | HunyuanVideo | 文生视频、图生视频及衍生任务 | [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) |
| 视频模型 | HunyuanVideo-1.5 | 更轻量的视频生成路线 | [Tencent-Hunyuan/HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) |
| 视频模型 | CogVideo | 可编程视频生成与 Diffusers 生态 | [THUDM/CogVideo](https://github.com/THUDM/CogVideo) |
| 研究框架 | Open-Sora | 训练、研究和完整生成管线 | [hpcaitech/Open-Sora](https://github.com/hpcaitech/Open-Sora) |
| Python 库 | Diffusers | 脚本化推理、模型组件与管线开发 | [huggingface/diffusers](https://github.com/huggingface/diffusers) |
| 官方 Skills | Wan-skills | 参考官方 Agent Skill 的目录与执行方式 | [Wan-Video/Wan-skills](https://github.com/Wan-Video/Wan-skills) |

完整机器可读目录见 [`catalog/projects.json`](catalog/projects.json)。

## 项目结构

```text
.
├── .github/workflows/validate.yml
├── catalog/projects.json
├── docs/LOCAL_SETUP.md
├── workflows/
│   ├── README.md
│   ├── models.json
│   ├── wan22_t2v_4step.json
│   ├── wan22_i2v_4step.json
│   └── wan22_long_video_3shot.json.gz
├── scripts/
│   ├── download_workflow_models.py
│   ├── materialize_workflows.py
│   ├── scaffold_project.py
│   ├── validate_catalog.py
│   └── validate_workflows.py
├── skills/ai-video-creation/
│   ├── SKILL.md
│   ├── references/
│   │   ├── model-selection.md
│   │   ├── troubleshooting.md
│   │   └── workflow-contract.md
│   └── templates/video-brief.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## 维护原则

- **官方优先**：模型和框架优先链接官方组织仓库。
- **不写死热度**：不维护 Stars 数，避免 README 很快失真。
- **不伪造能力**：无法从上游确认的版本、节点、模型或许可证，不写成确定结论。
- **估算必须标注**：显存、速度和生成时长只能作为环境相关估算。
- **商业使用先审许可**：仓库采用 MIT 许可证，不代表所收录模型或权重也能按 MIT 使用。
- **先做最小样片**：先用短时长、低分辨率和固定种子验证流程，再扩大分辨率与镜头数量。
- **结构验证不等于 GPU 验证**：JSON 连接、节点和模型引用可以自动检查，但真实生成仍需匹配的 GPU 环境。

## 贡献

提交前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，并运行：

```bash
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python -m py_compile scripts/*.py
```

## 免责声明

本仓库是工作流与资源索引，不托管模型权重，也不替代上游许可证、模型卡、安全说明和部署文档。使用任何第三方项目、模型或生成内容前，请自行核对适用法律、平台规则与商业授权条件。
