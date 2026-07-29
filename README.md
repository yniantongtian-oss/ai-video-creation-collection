# AI Video Creation Collection

面向 **长篇视频、网络研究、开放素材、AI 文案、配音字幕、自动剪辑、视频生成和 Agent Skills** 的可执行资源库。

本仓库把“查资料、找素材、写文案、做分镜、配音字幕、分章渲染、最终成片”组织成可复现、可断点续跑的工程流程。核心项目优先采用官方仓库或原作者仓库；模型、API、素材和二进制的许可证仍需在发布前核对。

## 核心能力

- 制作 **60–360 分钟**长篇纪录片、科普、课程和专题视频。
- 批量读取 PDF、DOCX、PPTX、网页、字幕、表格和本地资料。
- 为研究资料保留 SHA-256、页码、幻灯片和来源标记。
- 逐来源摘要、生成章节大纲、逐章检索和逐章写稿。
- 为一小时以上视频规划数百个视觉镜头。
- 搜索 Wikimedia Commons、Openverse、Pexels、Pixabay 素材。
- 记录素材作者、来源页、许可证、署名和文件哈希。
- 自动下载素材默认只是候选，审核后才能进入成片。
- 使用 Edge TTS 分章配音并生成 SRT 字幕。
- 使用 FFmpeg 逐镜头缓存、逐章渲染、最终拼接和写入章节元数据。
- 使用 MoneyPrinterTurbo 生成短视频。
- 使用 NarratoAI 做已有视频解说和自动剪辑。
- 使用 VideoLingo 做字幕、翻译和多语言配音。
- 使用 Auto-Editor 做静音、运动、字幕粗剪和专业工程导出。
- 使用 Wan2.2 ComfyUI 工作流生成缺失的 AI 镜头。

## 90 分钟长视频快速开始

### 1. 安装

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection

python scripts/install_web_media_stack.py --profile full
python scripts/install_longform_stack.py
python scripts/install_auto_editor.py
```

只查看安装计划：

```bash
python scripts/install_longform_stack.py --dry-run
```

编辑本地配置：

```text
tools/longform/.env
```

至少填写：

```text
LONGFORM_LLM_BASE_URL=https://你的服务地址/v1
LONGFORM_LLM_API_KEY=你的密钥
LONGFORM_LLM_MODEL=你的模型名称
```

### 2. 创建项目

```bash
python scripts/scaffold_longform_project.py \
  --name "空间太阳能电站完整纪录片" \
  --topic "空间太阳能电站的历史、原理、工程方案、争议与未来" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --audience "对科技感兴趣的大众观众"
```

默认约生成：

```text
13 个章节
约 23,400 个中文旁白字符
约 540 个视觉段落
```

### 3. 放入资料

把 PDF、DOCX、PPTX、TXT、Markdown、网页正文和字幕放进：

```text
projects/空间太阳能电站完整纪录片/research/inbox/
```

### 4. 研究、写稿和镜头规划

```bash
python scripts/run_longform_project.py \
  --project "projects/空间太阳能电站完整纪录片" \
  research
```

### 5. 搜索候选素材

```bash
python scripts/run_longform_project.py \
  --project "projects/空间太阳能电站完整纪录片" \
  assets \
  --execute-search \
  --download-first 1
```

### 6. 审核素材

列出候选：

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/空间太阳能电站完整纪录片/manifests/assets.jsonl" \
  --candidates
```

批准素材：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/空间太阳能电站完整纪录片/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "已核对内容、来源页、许可证和署名要求"
```

### 7. 配音、渲染和拼接

```bash
python scripts/run_longform_project.py \
  --project "projects/空间太阳能电站完整纪录片" \
  produce
```

素材未审核时会停止并输出：

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

这不是故障，而是版权和相关性审核闸门。

### 8. 最终输出

```text
outputs/final/<项目名称>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
```

完整指南：[`docs/LONGFORM_VIDEO_PRODUCTION.md`](docs/LONGFORM_VIDEO_PRODUCTION.md)

## 长视频为什么采用分章流水线

长视频不能把几万字资料和数百素材一次交给模型或渲染器。本仓库采用：

```text
资料入库
→ 逐来源摘要
→ 全片大纲
→ 逐章检索
→ 逐章写稿
→ 逐章镜头表
→ 素材审核
→ 逐章配音
→ 逐章渲染
→ 最终拼接
```

一章失败时，只重跑该章：

```bash
python scripts/longform_pipeline.py \
  --project "projects/<name>" \
  write \
  --chapter 4 \
  --force

python scripts/render_longform_narration.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force

python scripts/render_longform_chapters.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force
```

查看状态：

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  status
```

## 长视频主 Skill

```text
skills/longform-documentary-producer
```

它负责：

1. 选择适合的长视频规格和章节数；
2. 建立研究语料库；
3. 逐来源摘要和事实核查；
4. 生成章节大纲和长文案；
5. 规划数百镜头；
6. 搜索并审核开放授权素材；
7. 分章配音、字幕和渲染；
8. 最终拼接并生成章节时间戳；
9. 在任一阶段失败后从断点继续。

## 网络研究与短视频

主入口：

```text
skills/web-media-producer
```

安装档位：

| 档位 | 内容 | 场景 |
|---|---|---|
| `core` | yt-dlp、gallery-dl、Trafilatura | 网页研究和素材归档 |
| `creator` | core + MoneyPrinterTurbo | 主题到短视频 |
| `full` | creator + NarratoAI + VideoLingo | 已有视频分析、影视解说和多语言配音 |

```bash
python scripts/install_web_media_stack.py --profile core
python scripts/install_web_media_stack.py --profile creator
python scripts/install_web_media_stack.py --profile full
```

完整指南：

- [`docs/WEB_MEDIA_PRODUCTION.md`](docs/WEB_MEDIA_PRODUCTION.md)
- [`docs/WEB_MEDIA_APP_SETUP.md`](docs/WEB_MEDIA_APP_SETUP.md)

## AI 自动剪辑

```text
skills/ai-video-editing
skills/auto-editor
skills/auto-editor-effects
skills/auto-editor-transcribe
skills/auto-editor-export
```

安装：

```bash
python scripts/install_auto_editor.py
python scripts/check_video_editing_tools.py
```

第一次必须预览切点：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

完整指南：[`docs/VIDEO_EDITING_SETUP.md`](docs/VIDEO_EDITING_SETUP.md)

## ComfyUI 视频生成工作流

| 工作流 | 文件 | 默认规格 |
|---|---|---|
| Wan2.2 文生视频 | `workflows/wan22_t2v_4step.json` | 约 5 秒 |
| Wan2.2 图生视频 | `workflows/wan22_i2v_4step.json` | 约 5 秒 |
| 三镜头连续视频 | `workflows/wan22_long_video_3shot.json.gz` | 约 15 秒 |

展开压缩工作流：

```bash
python scripts/materialize_workflows.py
```

下载工作流模型前先预览：

```bash
python scripts/download_workflow_models.py \
  --workflow wan22_i2v_4step.json \
  --comfyui /path/to/ComfyUI \
  --dry-run
```

## Skills

```text
skills/longform-documentary-producer   60–360 分钟长篇视频
skills/web-media-producer              网络研究和素材自动成片
skills/moneyprinterturbo-video         主题到短视频
skills/ai-video-creation               AI 视频模型和工作流规划
skills/ai-video-editing                已有素材自动剪辑
skills/auto-editor                     基础自动剪辑
skills/auto-editor-effects             视频效果
skills/auto-editor-transcribe          转写和台词剪辑
skills/auto-editor-export              专业剪辑工程导出
```

## 关键脚本

```text
scripts/install_longform_stack.py        安装长视频运行环境
scripts/scaffold_longform_project.py      创建长视频项目
scripts/ingest_longform_corpus.py         资料提取和检索索引
scripts/longform_pipeline.py              摘要、大纲、文案和镜头
scripts/build_longform_asset_plan.py      批量素材搜索计划
scripts/media_asset_manifest.py           素材许可和批准
scripts/render_longform_narration.py      分章配音和字幕
scripts/build_longform_timeline.py        素材到镜头匹配
scripts/render_longform_chapters.py       分章渲染
scripts/assemble_longform_video.py        最终拼接和章节元数据
scripts/longform_preflight.py             环境、磁盘和质量预检
scripts/run_longform_project.py           总控命令
```

## 验证仓库

```bash
python scripts/materialize_workflows.py
python scripts/validate_catalog.py
python scripts/validate_workflows.py
python -m json.tool tools/web-media-stack.lock.json >/dev/null
python -m json.tool tools/longform-stack.lock.json >/dev/null
python -m py_compile scripts/*.py skills/moneyprinterturbo-video/mpt_agent.py
```

## 维护原则

- **长视频必须分章**：不使用一个超长提示词或一次性整片渲染。
- **来源可追溯**：事实保留来源标记，资料不足写 `NEEDS_SOURCE`。
- **素材先审核**：自动下载只是候选，不能直接进入成片。
- **授权优先**：优先公共领域、CC、平台授权和用户自有素材。
- **原始素材只读**：所有结果输出到项目目录，不覆盖原文件。
- **断点续跑**：已有摘要、配音片段、镜头缓存和章节成片默认跳过。
- **密钥不入库**：真实 API Key、模型、原视频、音频和成片均被 Git 忽略。
- **不伪造完成**：没有实际生成 MP4 时，不得声称视频已经完成。
- **商业使用再核验**：仓库 MIT 许可证不改变第三方软件、模型、音色、素材和编解码器条款。

## 第三方许可证

- 第三方来源和许可证：[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
- 视频项目目录：[`catalog/projects.json`](catalog/projects.json)
- 长视频工具目录：[`catalog/longform-tools.json`](catalog/longform-tools.json)
- 文档索引：[`docs/README.md`](docs/README.md)

## 免责声明

本仓库不授予第三方素材、模型、音色、字体、音乐或商业影视作品的版权，也不替代法律审查。自动摘要、长文案、字幕、镜头匹配、许可证元数据和最终成片必须经过人工复核。不得使用本仓库绕过登录、付费墙、验证码、地区限制、robots、平台安全机制或 DRM。
