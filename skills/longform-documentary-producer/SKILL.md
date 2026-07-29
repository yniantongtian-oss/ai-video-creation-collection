---
name: longform-documentary-producer
description: 让 Codex 制作 60 分钟以上的长篇纪录片、科普、课程、历史叙事、调查解释或专题视频。负责批量读取 PDF、DOCX、PPTX、网页、字幕和本地资料，建立可检索语料库，逐来源摘要，生成多章大纲和数万字文案，批量规划数百镜头，搜索并审核图片/视频/音频素材，逐章配音、字幕、渲染并最终拼接。适用于“一小时以上视频”“超长文案和大量素材”“多章节系列合成长片”“失败后只重跑一章”等任务。必须保留事实来源和素材许可证，不允许用一个超长提示词或一次性渲染整片。
metadata:
  version: 1.0.0
  language: zh-CN
  orchestrates:
    - web-media-producer
    - moneyprinterturbo-video
    - ai-video-editing
    - NarratoAI
    - VideoLingo
    - Edge-TTS
    - FFmpeg
---

# Codex 长篇视频制作

本 Skill 面向 60–360 分钟视频。长视频必须采用章节化流水线：

```text
项目规格
→ 研究资料入库
→ 逐来源摘要
→ 全片章节大纲
→ 逐章检索和写稿
→ 逐章镜头规划
→ 批量搜索开放授权素材
→ 人工/Codex 相关性与版权审核
→ 逐章配音和字幕
→ 逐章素材匹配与渲染
→ 最终拼接、章节元数据和质量报告
```

不得把短视频生成器简单设置成 60 分钟。不得一次把所有资料塞进一个模型请求。不得一次渲染整片。

## 一、默认设计

用户只说明“一个多小时”而没有给具体规格时，采用：

- 目标时长：90 分钟；
- 画幅：16:9，1920×1080，30 fps；
- 章节：约 13 章，每章约 7 分钟；
- 中文旁白：每分钟约 260 字符，总计约 23,400 字符；
- 视觉节奏：约每 10 秒更换主要画面，总计约 540 个镜头段；
- 编码：H.264 + AAC；
- 视频码率：8 Mbps；
- 字幕：独立 SRT，并在 MP4 中附加字幕轨；
- 自动下载素材全部先作为候选，默认 `selected=false`；
- 每章独立配音和渲染，支持断点续跑。

用户明确要求的时长、画幅、语言、风格、平台和受众优先。

## 二、安装

仓库根目录执行：

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/install_longform_stack.py
python scripts/install_auto_editor.py
```

先预览而不安装：

```bash
python scripts/install_longform_stack.py --dry-run
```

长视频环境变量位于：

```text
tools/longform/.env
```

至少配置：

```text
LONGFORM_LLM_BASE_URL
LONGFORM_LLM_API_KEY
LONGFORM_LLM_MODEL
```

不得打印、提交或复述密钥。

## 三、创建项目

```bash
python scripts/scaffold_longform_project.py \
  --name "项目名称" \
  --topic "视频主题" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --audience "目标观众" \
  --style "纪录片式科普，信息密度高但表达自然"
```

项目目录：

```text
projects/<name>/
├── brief.md
├── project.json
├── research/
│   ├── inbox/
│   ├── extracted/
│   ├── summaries/
│   ├── sources.jsonl
│   ├── chunks.jsonl
│   └── index.sqlite
├── outline/
├── manifests/
├── chapters/
│   ├── 01/
│   ├── 02/
│   └── ...
├── state/
├── logs/
└── outputs/
```

所有资料、素材、中间文件和成片都放在项目目录中。

## 四、资料入库

把资料放进：

```text
projects/<name>/research/inbox/
```

支持：

```text
PDF
DOCX
PPTX
TXT
Markdown
HTML
CSV / TSV
JSON
SRT / VTT
```

然后运行：

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<name>"
```

也可直接指定多个文件或目录：

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<name>" \
  --input "/path/to/documents" \
  --input "/path/to/subtitles"
```

脚本会：

1. 复制外部文档到项目；
2. 计算 SHA-256；
3. PDF 按页、PPTX 按幻灯片保留定位；
4. 提取正文；
5. 切成重叠语料块；
6. 写入 JSONL 和 SQLite 检索索引；
7. 跳过已经入库的相同文件。

扫描版 PDF 无文本时不能伪造读取结果，应先使用可靠 OCR 或要求提供可复制文本版本。

## 五、研究、大纲、文案和镜头

一条命令完成：

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  research
```

它会按以下顺序执行：

```text
逐来源摘要
→ 全片大纲
→ 逐章检索资料
→ 逐章撰写文案
→ 逐章生成镜头表
```

单独运行：

```bash
python scripts/longform_pipeline.py --project "projects/<name>" summarize
python scripts/longform_pipeline.py --project "projects/<name>" plan
python scripts/longform_pipeline.py --project "projects/<name>" write
python scripts/longform_pipeline.py --project "projects/<name>" shots
```

只重做第 4 章：

```bash
python scripts/longform_pipeline.py \
  --project "projects/<name>" \
  write \
  --chapter 4 \
  --force

python scripts/longform_pipeline.py \
  --project "projects/<name>" \
  shots \
  --chapter 4 \
  --force
```

每章必须输出：

```text
brief.md
script.md
narration.txt
claims.json
open-questions.json
shots.json
```

`script.md` 保留 `[S:source_id#locator]` 来源标记；`narration.txt` 是不朗读来源标记的配音稿。资料不足处必须写 `NEEDS_SOURCE`。

## 六、长视频素材策略

不要为每个镜头进行一次独立网络搜索。先把镜头查询去重为每章 8–15 个查询组：

```bash
python scripts/build_longform_asset_plan.py \
  --project "projects/<name>"
```

执行 Wikimedia Commons、Openverse、Pexels 和 Pixabay 搜索，并为每个平台下载一个候选：

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  assets \
  --execute-search \
  --download-first 1
```

候选进入：

```text
assets/global/images/
assets/global/videos/
manifests/assets.jsonl
```

自动下载的素材始终为候选，不得直接进入成片。

### 素材不足时的优先级

1. Wikimedia Commons 的公共领域、CC BY、CC BY-SA 档案；
2. Openverse 中许可证明确的图片和音频；
3. Pexels、Pixabay 的平台授权 B-roll；
4. 官方机构、博物馆、大学和政府公开资料；
5. 用户自有素材；
6. 用 ComfyUI 自制缺失的概念画面；
7. 自制地图、时间线、流程图和数据图；
8. 仅在合法合理引用范围内使用必要短片，并保留单独法律审核，不自动认定可发布。

不得用来源不明的影视、音乐、图库或社交平台搬运内容填满一小时。

## 七、素材审核和批准

列出候选：

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/<name>/manifests/assets.jsonl" \
  --candidates
```

Codex 应逐项查看：

- 画面是否与旁白匹配；
- 是否有水印、低清、错误人物或错误地点；
- 来源页是否存在；
- 许可证是否允许当前用途；
- 是否需要作者署名；
- 是否包含隐私、人像、商标、未成年人或敏感内容风险。

批准一个素材：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<name>/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "已核对画面相关性、来源页和许可证"
```

批量批准：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<name>/manifests/assets.jsonl" \
  --ids-file approved-assets.txt \
  --value true
```

取消批准：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<name>/manifests/assets.jsonl" \
  --id "asset-id" \
  --value false
```

批准时会重新验证文件哈希、来源、许可证、作者署名和许可说明。

## 八、配音、时间线和章节渲染

一条命令：

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  produce
```

它会执行：

```text
版权预检
→ 逐章分段配音
→ 合并逐章字幕
→ 素材自动匹配
→ 逐镜头缓存
→ 逐章渲染
→ 最终拼接
→ 全片字幕与章节时间戳
```

如果没有足够的已批准素材，命令必须停止并输出：

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

不得绕过该闸门。

### 单独运行

```bash
python scripts/render_longform_narration.py \
  --project "projects/<name>"

python scripts/build_longform_timeline.py \
  --project "projects/<name>"

python scripts/render_longform_chapters.py \
  --project "projects/<name>"

python scripts/assemble_longform_video.py \
  --project "projects/<name>"
```

只重做一章：

```bash
python scripts/render_longform_narration.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force

python scripts/build_longform_timeline.py \
  --project "projects/<name>" \
  --chapter 4

python scripts/render_longform_chapters.py \
  --project "projects/<name>" \
  --chapter 4 \
  --force
```

重做单章后，再运行最终拼接。

## 九、现有视频分析

用户提供长视频、采访、课程、纪录片或大量视频素材时：

1. 使用 yt-dlp 或用户本地文件取得合法素材；
2. 使用 VideoLingo、NarratoAI 或 Auto-Editor 转录音频；
3. 按固定间隔和场景切换抽帧；
4. 让视觉模型分析抽帧，而不是声称一次看完数小时原视频；
5. 将字幕、时间码、人物、地点、镜头类型和主题标签写入项目；
6. 再参与章节检索和素材匹配。

不得未经运行视频理解或抽帧步骤就声称已经看完所有素材。

## 十、质量预检

任何阶段均可运行：

```bash
python scripts/longform_preflight.py \
  --project "projects/<name>" \
  --stage setup
```

可选阶段：

```text
setup
research
writing
assets
narration
render
final
```

预检内容包括：

- 长视频虚拟环境；
- LLM 配置；
- Edge TTS；
- FFmpeg；
- 可用磁盘空间；
- 资料来源和语料块；
- 来源摘要和章节大纲；
- 文案长度和章节完整度；
- 镜头数量；
- 已批准素材和许可证；
- 时间线黑屏占位；
- 配音章数和时长；
- 已渲染章节和时长。

渲染前预检失败时不得继续。

## 十一、断点和状态

查看状态：

```bash
python scripts/run_longform_project.py \
  --project "projects/<name>" \
  status
```

状态文件：

```text
state/pipeline.json
chapters/<id>/status.json
```

已有摘要、文案、语音片段、镜头视频和章节视频默认跳过。只有用户明确要求或产物损坏时使用 `--force`。

## 十二、最终交付

最终目录至少包括：

```text
outputs/final/<project>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
outline/outline.json
outline/chapter-map.csv
manifests/assets.jsonl
research/sources.jsonl
chapters/*/script.md
chapters/*/claims.json
```

交付前检查：

1. `assembly-report.json` 的时长检查通过；
2. 总时长符合用户要求；
3. 无 `NEEDS_SOURCE` 遗留，或已明确列为待核查；
4. 无占位镜头；
5. 无丢失素材和哈希变化；
6. 字幕、旁白和画面同步；
7. 音量一致，无明显爆音和长时间静音；
8. 开头、章节转场和结尾完整；
9. 署名清单满足许可证；
10. 没有实际生成 MP4 时，不得声称视频已完成。

## 十三、禁止事项

- 不用一个超长提示词生成整部一小时文案；
- 不把所有原始资料无筛选塞入上下文；
- 不一次渲染完整长片；
- 不自动批准下载的素材；
- 不绕过登录、付费墙、验证码、地区限制、robots 或 DRM；
- 不因为来源很多就省略事实核查；
- 不覆盖原始素材；
- 不在仓库提交 API Key、模型、原视频、音频、成片或大型缓存；
- 不在缺少实际运行结果时声称已经完成。
