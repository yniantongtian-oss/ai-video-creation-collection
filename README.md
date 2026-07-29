# AI Video Creation Collection

面向 **网络研究、AI 视频生成、自动剪辑、素材版权追踪、本地工作流与 Agent Skills** 的可执行资源库。

本仓库把“查资料、找素材、写文案、做分镜、配音字幕、剪辑成片”组织成可复现流程。核心项目优先采用官方仓库或原作者仓库；具体版本、许可证、模型权重、API 条款和硬件要求应在部署与发布前再次核对。

## 这个仓库能做什么

- 让 Codex 从公开网页、开放授权素材库和用户已授权链接收集文档、图片、视频与音频。
- 为每项素材记录来源、作者、许可证、SHA-256 和是否允许进入最终成片。
- 使用 MoneyPrinterTurbo 从主题或脚本生成文案、匹配素材、配音、字幕、音乐和最终短视频。
- 使用 NarratoAI 对用户自有或已获许可的长视频生成解说文案、配音与自动剪辑。
- 使用 VideoLingo 完成字幕识别、翻译、本地化和多语言配音。
- 使用 Auto-Editor 对已有素材做静音、运动、黑场、字幕和关键词粗剪，并导出专业剪辑工程。
- 使用三套 Wan2.2 ComfyUI 工作流完成文生视频、图生视频和三镜头连续视频。
- 使用项目脚手架生成 brief、研究目录、素材清单、文案、分镜和可复现参数。
- 通过 GitHub Actions 校验资源目录、工作流、Python 脚本和新项目骨架。

## 快速开始

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection

# 检查仓库本身
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python -m py_compile scripts/*.py

# 预览网络研究与成片工具安装计划，不下载任何内容
python scripts/install_web_media_stack.py --profile creator --dry-run

# 安装主题到短视频的默认组合
python scripts/install_web_media_stack.py --profile creator

# 创建一个可追溯的 90 秒竖屏视频项目
python scripts/scaffold_web_media_project.py \
  --name "空间太阳能电站科普" \
  --topic "空间太阳能电站如何向地面输送能量" \
  --duration 90 \
  --aspect-ratio 9:16 \
  --language zh-CN
```

## Codex 网络素材自动成片

主入口：

```text
skills/web-media-producer
```

它负责组织以下流程：

```text
主题与受众
→ 网络研究与来源核验
→ 开放授权或已获许可素材搜索
→ 素材清单与版权闸门
→ 原创文案与逐镜头分镜
→ 配音、字幕和音乐
→ 自动剪辑或专业工程导出
→ MP4、SRT、文案、分镜和来源清单
```

### 安装档位

| 档位 | 安装内容 | 适合场景 |
|---|---|---|
| `core` | yt-dlp、gallery-dl、Trafilatura | 网页研究、视频/图片下载与素材归档 |
| `creator` | `core` + MoneyPrinterTurbo | 主题、文案、素材、配音、字幕到短视频 |
| `full` | `creator` + NarratoAI + VideoLingo | 影视解说、已有视频分析、翻译和多语言配音 |

```bash
python scripts/install_web_media_stack.py --profile core
python scripts/install_web_media_stack.py --profile creator
python scripts/install_web_media_stack.py --profile full
```

第三方工具被安装或克隆到：

```text
tools/web-media/
```

该目录被 Git 忽略。仓库只保存审核过的仓库地址、提交 SHA、许可证与安装清单：

```text
tools/web-media-stack.lock.json
```

配置模板：

```text
config/web-media.env.example
```

首次安装会创建本地文件：

```text
tools/web-media/.env
```

真实 API Key 不得提交到 Git、写进文案或打印到日志。

### 搜索开放授权素材

Wikimedia Commons：

```bash
python scripts/search_open_media.py \
  --provider commons \
  --media-type image \
  --query "space based solar power" \
  --limit 20 \
  --output "projects/空间太阳能电站科普/research/search-results/commons.json"
```

Pexels 视频并下载前三个候选：

```bash
python scripts/search_open_media.py \
  --provider pexels \
  --media-type video \
  --query "satellite earth solar panels" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/空间太阳能电站科普/assets/videos" \
  --manifest "projects/空间太阳能电站科普/manifests/assets.jsonl"
```

还支持：

```text
Openverse：Creative Commons / 公共领域图片与音频发现
Pixabay：图片和视频素材平台 API
```

搜索下载的文件默认只是候选素材：

```json
"selected": false
```

Codex 必须检查内容、相关性、清晰度、隐私和许可证后，才能将其选入镜头表。

### 收集公开网页资料

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/official-document" \
  --project "projects/空间太阳能电站科普" \
  --asset-id "official-source-001" \
  --license "Research reference; quotation limits apply" \
  --rights-status restricted
```

`restricted` 文档可用于研究和事实核查，但不能直接把其大段正文作为旁白或画面素材。

### 下载用户已授权链接

```bash
python scripts/ingest_authorized_source.py \
  --type video \
  --url "https://example.com/public-video" \
  --project "projects/项目名称" \
  --asset-id "user-video-001" \
  --license "User owns or has permission to reuse" \
  --rights-status permission-granted \
  --permission-note "用户确认拥有再利用许可"
```

下载包装器故意不提供 Cookie、密码、浏览器会话、付费墙或 DRM 绕过参数。

### 素材版权闸门

最终剪辑前必须运行：

```bash
python scripts/media_asset_manifest.py validate \
  --manifest "projects/项目名称/manifests/assets.jsonl"
```

默认允许：

```text
public-domain
cc0
cc-by
cc-by-sa
provider-licensed
user-owned
permission-granted
```

默认阻止：

```text
unknown
restricted
```

完整安装、素材搜索、Codex 指令和使用边界见 [`docs/WEB_MEDIA_PRODUCTION.md`](docs/WEB_MEDIA_PRODUCTION.md)。

## MoneyPrinterTurbo Agent Skill

主题直接生成成片的入口：

```text
skills/moneyprinterturbo-video
```

在 Skill 目录中运行：

```bash
uv run --no-project --python 3.11 python mpt_agent.py \
  --subject "空间太阳能电站如何工作"
```

本仓库使用固定提交和 Git Blob SHA 校验上游官方助手脚本。默认生成中文 `9:16` 视频，并由上游流程完成素材匹配、配音、字幕、背景音乐和 MP4 输出。

当项目必须逐项使用指定文档或素材时，先使用 `web-media-producer` 建立素材清单和镜头表，再决定调用 MoneyPrinterTurbo 或 `ai-video-editing`。

## AI 自动剪辑

仓库已引入 Auto-Editor 的官方 Agent Skills，并提供中文统一入口：

```text
skills/ai-video-editing
skills/auto-editor
skills/auto-editor-effects
skills/auto-editor-transcribe
skills/auto-editor-export
```

下载官方二进制并检查环境：

```bash
python scripts/install_auto_editor.py
python scripts/check_video_editing_tools.py
```

第一次剪辑先用 `--preview` 检查自动切点：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

确认后再输出新文件，不覆盖原素材：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  -o outputs/input_cut.mp4
```

支持声音、运动、黑场、字幕和关键词检测，也可进行变速、缩放、音量处理、Logo/画中画叠加，并导出 Premiere、DaVinci Resolve、Final Cut Pro、Shotcut、Kdenlive 或分镜序列。完整说明见 [`docs/VIDEO_EDITING_SETUP.md`](docs/VIDEO_EDITING_SETUP.md)。

## ComfyUI 视频生成工作流

| 工作流 | 文件 | 默认规格 | 核心逻辑 |
|---|---|---|---|
| 文生视频 | [`workflows/wan22_t2v_4step.json`](workflows/wan22_t2v_4step.json) | 81 帧、16 fps、约 5 秒 | Wan2.2 T2V 双模型、4-step 双阶段采样 |
| 图生视频 | [`workflows/wan22_i2v_4step.json`](workflows/wan22_i2v_4step.json) | 81 帧、16 fps、约 5 秒 | 参考图作为首帧，Wan2.2 I2V 双阶段采样 |
| 三镜头长视频 | `workflows/wan22_long_video_3shot.json` | 241 帧、16 fps、约 15.1 秒 | 上一镜头末帧续写，删除重复边界帧后拼接 |

三镜头工作流以无损 gzip 源文件保存。克隆后执行：

```bash
python scripts/materialize_workflows.py
python scripts/validate_workflows.py
```

### 模型下载

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

确认后移除 `--dry-run`。模型文件、目标目录和官方来源记录在 [`workflows/models.json`](workflows/models.json)。模型权重很大，运行前应核对磁盘、模型条款以及 ComfyUI、PyTorch、CUDA 和驱动兼容性。

## Skills 总览

```text
skills/web-media-producer         网络研究、素材、文案、分镜和成片总控
skills/moneyprinterturbo-video    主题或脚本直接生成短视频
skills/ai-video-creation          AI 视频生成需求分析与 ComfyUI 路由
skills/ai-video-editing           已有素材自动剪辑中文入口
skills/auto-editor                基础自动剪辑
skills/auto-editor-effects        变速、缩放、叠加与动画
skills/auto-editor-transcribe     转写与按台词剪辑
skills/auto-editor-export         专业剪辑工程导出
```

在支持 Agent Skills 的 Codex 或其他工具中加载对应目录即可。

## 推荐起点

| 类型 | 项目 | 适合场景 | 上游 |
|---|---|---|---|
| 全流程短视频 | MoneyPrinterTurbo | 文案、素材、配音、字幕、音乐与成片 | [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) |
| 影视解说 | NarratoAI | 已有视频理解、解说、配音和自动剪辑 | [linyqh/NarratoAI](https://github.com/linyqh/NarratoAI) |
| 视频本地化 | VideoLingo | 字幕识别、翻译、术语和多语言配音 | [Huanshere/VideoLingo](https://github.com/Huanshere/VideoLingo) |
| 视频下载 | yt-dlp | 公开或已授权视频、音频、字幕和元数据 | [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| 图片下载 | gallery-dl | 公开或已授权图片图库 | [mikf/gallery-dl](https://github.com/mikf/gallery-dl) |
| 网页提取 | Trafilatura | 文章正文、元数据和研究资料 | [adbar/trafilatura](https://github.com/adbar/trafilatura) |
| 自动剪辑 | Auto-Editor | 静音/运动/字幕粗剪和工程导出 | [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor) |
| 工作流引擎 | ComfyUI | 节点式本地生成、API 与可视化调试 | [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) |
| 视频模型 | Wan2.2 | 文生视频、图生视频及官方扩展能力 | [Wan-Video/Wan2.2](https://github.com/Wan-Video/Wan2.2) |
| 视频模型 | LTX-Video / LTX-2 | 视频生成、关键帧控制与音视频能力 | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) |
| Python 库 | Diffusers | 脚本化推理、训练与服务化 | [huggingface/diffusers](https://github.com/huggingface/diffusers) |

完整机器可读目录见 [`catalog/projects.json`](catalog/projects.json)。

## 项目结构

```text
.
├── .github/workflows/validate.yml
├── catalog/projects.json
├── config/web-media.env.example
├── docs/
│   ├── LOCAL_SETUP.md
│   ├── VIDEO_EDITING_SETUP.md
│   └── WEB_MEDIA_PRODUCTION.md
├── tools/web-media-stack.lock.json
├── workflows/
├── scripts/
│   ├── check_video_editing_tools.py
│   ├── ingest_authorized_source.py
│   ├── install_auto_editor.py
│   ├── install_web_media_stack.py
│   ├── media_asset_manifest.py
│   ├── scaffold_project.py
│   ├── scaffold_web_media_project.py
│   ├── search_open_media.py
│   ├── validate_catalog.py
│   └── validate_workflows.py
├── skills/
│   ├── web-media-producer/
│   ├── moneyprinterturbo-video/
│   ├── ai-video-creation/
│   ├── ai-video-editing/
│   ├── auto-editor/
│   ├── auto-editor-effects/
│   ├── auto-editor-export/
│   └── auto-editor-transcribe/
├── THIRD_PARTY_NOTICES.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## 维护原则

- **官方优先**：模型、框架、工具和 Skills 优先采用官方组织或原作者仓库。
- **版本锁定**：自动安装的第三方工具记录明确提交 SHA，不默认跟随移动的主分支。
- **不写死热度**：不维护 Stars 排名，避免快速失真。
- **不伪造能力**：无法确认的版本、参数、硬件要求、许可证或运行结果不写成事实。
- **搜索不等于授权**：能够发现或下载素材，不代表拥有复制、改编或再发布权。
- **候选先审查**：自动下载素材默认 `selected=false`，通过相关性与版权检查后才能进入成片。
- **不绕过访问控制**：不提供 DRM、付费墙、登录、验证码或平台安全机制的绕过流程。
- **研究尊重来源**：不整篇复制文章、字幕、书籍或付费内容，只保留必要摘要、短引文与事实记录。
- **剪辑先预览**：自动粗剪先检查切点，再渲染到新文件，不覆盖原素材。
- **结构验证不等于运行验证**：静态检查通过不代表模型推理、API 调用或成片质量已经实测。

## 贡献

提交前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)，并运行：

```bash
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python scripts/install_web_media_stack.py --profile full --dry-run
python -m py_compile scripts/*.py skills/moneyprinterturbo-video/mpt_agent.py
```

第三方内容的来源、许可证和导入版本应同步记录到 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 免责声明

本仓库是工作流、Agent Skills、安装脚本和资源索引，不托管模型权重、Auto-Editor Release 二进制或第三方媒体素材，也不替代上游许可证、素材平台条款、模型卡、安全说明和法律审查。自动文案、字幕、事实、切点、配音、素材许可和导出工程必须经过人工复核。使用任何第三方代码、模型、API、图片、视频、音频或生成内容前，请核对适用法律、平台规则、隐私要求与商业授权条件。
