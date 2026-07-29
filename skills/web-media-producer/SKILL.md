---
name: web-media-producer
description: 让 Codex 从公开网页、开放授权素材库和用户已授权的链接收集文档、图片、视频与音频，保留来源和许可证，完成事实核查、中文文案、镜头表、配音、字幕、剪辑和最终成片。适用于“全网搜素材做视频”“查资料后自动生成短视频”“从多个来源混剪并配文案”“做科普/新闻解释/产品介绍/影视解说”“把已有视频翻译配音”等任务。默认优先使用开放授权来源和本仓库工具，不绕过登录、付费墙、DRM、robots 或平台限制。
metadata:
  version: 1.0.0
  language: zh-CN
  orchestrates:
    - moneyprinterturbo-video
    - ai-video-editing
    - NarratoAI
    - VideoLingo
    - yt-dlp
    - gallery-dl
    - Trafilatura
---

# Codex 全流程网络素材视频制作

本 Skill 把用户的目标转换为一条可执行、可追溯的制作流水线：

```text
主题与受众
→ 网络研究与来源核验
→ 开放授权/已获许可素材搜索
→ 素材清单与版权闸门
→ 文案与镜头表
→ 配音、字幕、音乐
→ 自动粗剪与包装
→ 成片、工程文件、来源清单与事实核查报告
```

“全网”表示在公开可访问且允许使用的来源中进行广泛研究，不代表无限制抓取整个互联网。不得把技术上可下载的内容自动视为可再发布素材。

## 一、启动前提

仓库根目录运行：

```bash
python scripts/install_web_media_stack.py --profile creator
python scripts/check_video_editing_tools.py
```

需要影视解说和多语言配音时使用完整配置：

```bash
python scripts/install_web_media_stack.py --profile full
```

配置文件位置：

```text
tools/web-media/.env
```

该文件由 `config/web-media.env.example` 创建并被 Git 忽略。Agent 不得打印、提交或复述其中的密钥。

## 二、先建立项目，不直接乱下素材

```bash
python scripts/scaffold_web_media_project.py \
  --name "项目名称" \
  --topic "研究主题" \
  --duration 60 \
  --aspect-ratio 9:16 \
  --language zh-CN
```

项目至少包含：

```text
projects/<name>/
├── brief.md
├── project.json
├── research/
├── assets/
├── manifests/assets.jsonl
├── script/script.md
├── storyboard/storyboard.csv
├── edit/edit-plan.json
├── subtitles/
├── voice/
└── outputs/
```

所有中间产物都放进该项目，不能散落在仓库根目录。

## 三、需求与交付规格

优先从用户现有信息提取，不重复询问已经明确的内容。至少确定：

- `topic`：核心主题或问题；
- `goal`：解释、营销、新闻梳理、教程、故事、影视解说或翻译配音；
- `audience`：受众知识水平；
- `duration`：预计时长；
- `aspect_ratio`：9:16、16:9、1:1 或 4:5；
- `language`：文案、配音与字幕语言；
- `platform`：抖音、B站、视频号、YouTube 等；
- `source_scope`：开放网络、指定网站、用户提供文件或 URL；
- `commercial_use`：是否商用；
- `delivery`：成片、字幕、文案、剪辑工程和来源清单。

信息不足但能安全推进时，使用明确假设并写入 `brief.md`。

## 四、研究资料收集

### 4.1 研究原则

1. 优先原始资料、官方文档、论文、机构页面和可信新闻来源。
2. 搜索结果摘要只能用于发现来源，不能直接作为事实依据。
3. 每个关键事实记录标题、URL、作者/机构、发布日期和局限。
4. 不整篇复制文章、字幕、书籍章节或付费内容；只保存必要摘要和短引文。
5. 涉及最新新闻、价格、政策、人物身份、软件版本和产品规格时，必须重新联网核验。
6. 对矛盾来源保留不同说法，不擅自拼成确定结论。

### 4.2 提取公开网页正文

对于公开且允许访问的单个页面：

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/article" \
  --project "projects/项目名称" \
  --asset-id "source-001" \
  --license "Research reference; quotation limits apply" \
  --rights-status restricted
```

`restricted` 文档可以用于研究和事实核查，但不得直接把其正文作为视频素材或大段旁白。

不要用 Trafilatura 的批量爬取功能扫描整个站点，除非站点明确允许且用户确实需要。默认一次处理少量已选定页面。

## 五、素材搜索与下载

### 5.1 开放与素材平台来源

优先顺序：

1. Wikimedia Commons 公共领域或 Creative Commons 文件；
2. Openverse 聚合的 CC/公共领域图片与音频；
3. Pexels 图片和视频；
4. Pixabay 图片和视频；
5. Coverr（由 MoneyPrinterTurbo 当前支持时使用）；
6. 用户自有素材或已有书面许可的链接。

### 5.2 搜索示例

Wikimedia Commons：

```bash
python scripts/search_open_media.py \
  --provider commons \
  --media-type image \
  --query "space solar power station" \
  --limit 20 \
  --output "projects/项目名称/research/search-results/commons.json"
```

Pexels 视频并下载前三个候选：

```bash
python scripts/search_open_media.py \
  --provider pexels \
  --media-type video \
  --query "solar panels satellite earth" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/项目名称/assets/videos" \
  --manifest "projects/项目名称/manifests/assets.jsonl" \
  --output "projects/项目名称/research/search-results/pexels.json"
```

Pixabay：

```bash
python scripts/search_open_media.py \
  --provider pixabay \
  --media-type image \
  --query "satellite energy" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/项目名称/assets/images" \
  --manifest "projects/项目名称/manifests/assets.jsonl"
```

下载项目默认以 `selected=false` 写入素材清单。Codex 必须查看内容、相关性、清晰度和授权信息后，才能将其选入镜头表。

### 5.3 用户授权的普通链接

公开视频：

```bash
python scripts/ingest_authorized_source.py \
  --type video \
  --url "https://example.com/public-video" \
  --project "projects/项目名称" \
  --asset-id "user-video-001" \
  --license "User owns or has permission to reuse" \
  --rights-status permission-granted \
  --permission-note "用户在当前任务中确认拥有再利用许可"
```

公开图片图库：

```bash
python scripts/ingest_authorized_source.py \
  --type gallery \
  --url "https://example.com/public-gallery" \
  --project "projects/项目名称" \
  --asset-id "gallery-001" \
  --license "CC BY 4.0" \
  --license-url "https://creativecommons.org/licenses/by/4.0/" \
  --rights-status cc-by \
  --creator "作者名称" \
  --attribution "作者名称，CC BY 4.0"
```

不得使用本仓库脚本绕过登录、地区限制、付费墙、DRM、私密账号、验证码或平台反爬措施。脚本故意不提供浏览器 Cookie、账号密码和 DRM 绕过参数。

## 六、素材版权闸门

最终剪辑前必须运行：

```bash
python scripts/media_asset_manifest.py validate \
  --manifest "projects/项目名称/manifests/assets.jsonl"
```

允许的默认状态：

```text
public-domain
cc0
cc-by
cc-by-sa
provider-licensed
user-owned
permission-granted
```

以下状态禁止进入最终成片：

```text
unknown
restricted
```

CC BY 与 CC BY-SA 必须记录作者和许可证 URL；`permission-granted` 必须记录许可说明。最终片尾、简介或交付清单应包含必要署名。

## 七、文案与镜头表

### 7.1 文案要求

文案写入 `script/script.md`，结构至少包括：

1. 标题候选；
2. 前 3–8 秒钩子；
3. 背景与问题；
4. 核心解释或故事推进；
5. 证据、数据和例子；
6. 结论；
7. 行动引导；
8. 事实核查清单。

文案应原创表达。不要把多个来源句子简单拼接，也不要模仿某位在世创作者的独特表达风格。

### 7.2 镜头表要求

每个镜头写入 `storyboard/storyboard.csv`：

- 起止时间；
- 对应旁白；
- 视觉搜索词；
- 选用 `asset_id`；
- 推拉摇移、裁切、缩放和转场；
- 字幕；
- 对应事实来源；
- 状态。

镜头必须与文案语义匹配，不能只因“画面好看”使用无关素材。

## 八、自动选择制作路线

### 路线 A：主题直接生成短视频

适合：科普、营销、知识解释、社交媒体视频，不要求逐个使用用户指定素材。

加载：

```text
skills/moneyprinterturbo-video
```

MoneyPrinterTurbo 可以完成文案、Pexels/Pixabay/Coverr 素材、配音、字幕、音乐和成片。完成后把最终 MP4、任务目录、文案和素材来源记录并入当前项目。

### 路线 B：研究驱动、指定素材混剪

适合：必须使用指定文档、图片、视频或有严格镜头表的项目。

使用：

```text
skills/ai-video-editing
```

流程：

```text
素材预处理 → 旁白/配音 → 镜头拼接 → 字幕 → 音乐 → 自动粗剪
→ 人工抽检 → 导出 MP4 或 Premiere/Resolve 工程
```

先用 Auto-Editor/FFmpeg 做可复现粗剪；需要精修时导出专业剪辑工程。

### 路线 C：已有影视素材的解说与混剪

适合：用户有权使用的电影、短剧、纪录片或长视频，需要视觉理解、解说文案、配音和自动剪辑。

使用安装于：

```text
tools/web-media/apps/NarratoAI
```

NarratoAI 仅处理用户自有、公共领域或已获许可的视频。不要默认抓取商业影视作品再发布。

### 路线 D：翻译、字幕和多语言配音

适合：把已有视频翻译为另一种语言并生成单行字幕和配音。

使用安装于：

```text
tools/web-media/apps/VideoLingo
```

其功能包括 yt-dlp 输入、WhisperX 字幕识别、翻译、术语表和多种 TTS。必须检查原视频的使用权、翻译权和配音发布权。

## 九、质量检查

成片前后分别检查：

### 内容

- 每个关键事实有来源；
- 日期、数据、人物和机构名称准确；
- 没有把推测写成事实；
- 文案没有大段复制来源。

### 素材

- `asset_id` 与实际文件一致；
- 所有选中素材通过 manifest 校验；
- 需要署名的素材已生成署名清单；
- 没有水印、个人隐私、敏感信息或误导性画面。

### 视频

- 句首句尾未被误剪；
- 画面与旁白同步；
- 字幕无明显错字且时间轴正确；
- 配音清晰，音乐不过度压过人声；
- 横竖屏裁切没有切掉主体；
- 最终文件可播放，时长、分辨率、帧率符合要求。

## 十、最终交付

至少交付：

```text
outputs/final.mp4
script/script.md
storyboard/storyboard.csv
subtitles/final.srt
manifests/assets.jsonl
research/sources.md
edit/edit-plan.json
```

同时给出简短报告：

- 研究了哪些主要来源；
- 使用了哪些素材平台；
- 哪些素材需要署名；
- 使用哪条制作路线；
- 哪些步骤已实际运行；
- 哪些内容仍需要用户人工确认。

没有实际运行成片流程时，不能声称视频已经生成。没有通过素材版权闸门时，不能进入最终渲染。
