# AI Video Creation Collection

面向 **AI 视频创作、开源模型选型、本地工作流设计与 Agent Skill** 的可执行资源库。

本仓库不再维护容易过期的 Stars 排名，也不把未经核验的版本、显存需求或社区项目写成确定事实。核心项目优先收录官方仓库；具体版本、模型权重、许可证和硬件要求，应在部署前再次查看上游文档。

## 这个仓库能做什么

- 用结构化目录筛选 AI 视频模型、工作流框架和基础库。
- 安装 `ai-video-creation` Skill，让支持 Agent Skills 的助手按照统一流程完成需求分析、模型路由、镜头拆解、提示词规划和风险检查。
- 使用零第三方依赖的 Python 脚本，一键生成可直接填写的视频项目目录。
- 通过 GitHub Actions 自动检查资源目录和 Python 脚本，减少失效格式进入主分支。

## 快速开始

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection

# 检查结构化资源目录
python scripts/validate_catalog.py

# 创建一个 30 秒、16:9 的图生视频项目
python scripts/scaffold_project.py \
  --name "产品发布短片" \
  --duration 30 \
  --aspect-ratio 16:9 \
  --mode i2v
```

脚本会生成：

```text
projects/产品发布短片/
├── brief.md
├── manifest.json
├── prompts.md
└── shots.csv
```

## 安装 Skill

Skill 路径：

```text
skills/ai-video-creation
```

在支持 Agent Skills 的工具中，安装或加载该目录即可。示例指令：

```text
安装这个目录下的 Skill：/path/to/ai-video-creation-collection/skills/ai-video-creation
```

Skill 的职责不是凭空承诺“已生成视频”，而是：

1. 把用户需求转换为明确的视频制作 brief。
2. 根据任务类型、素材、硬件和授权要求选择候选技术路线。
3. 输出镜头表、提示词包、目录结构、执行步骤与验收标准。
4. 在提供具体安装命令前核对上游官方文档。
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
├── scripts/
│   ├── scaffold_project.py
│   └── validate_catalog.py
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

## 贡献

提交新项目或修改目录前，请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，并运行：

```bash
python scripts/validate_catalog.py
python -m py_compile scripts/*.py
```

## 免责声明

本仓库是工作流与资源索引，不托管模型权重，也不替代上游许可证、模型卡、安全说明和部署文档。使用任何第三方项目、模型或生成内容前，请自行核对适用法律、平台规则与商业授权条件。
