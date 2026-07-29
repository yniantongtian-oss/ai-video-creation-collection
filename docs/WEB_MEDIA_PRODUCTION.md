# Codex 网络资料与素材自动成片

本仓库现在支持让 Codex 完成以下流程：

```text
公开网络研究
→ 文档正文提取与事实核查
→ 开放授权图片/视频/音频搜索
→ 用户授权链接下载
→ 素材来源和许可证清单
→ 文案、分镜、配音、字幕、音乐
→ 自动剪辑、翻译配音或影视解说
→ 最终 MP4 与可追溯交付包
```

核心入口：

```text
skills/web-media-producer
```

主题直接生成成片：

```text
skills/moneyprinterturbo-video
```

## 1. 安装配置

需要先安装 `git` 和 `uv`。然后在仓库根目录运行：

```bash
python scripts/install_web_media_stack.py --profile creator
```

三个安装档位：

| 档位 | 内容 | 适合场景 |
|---|---|---|
| `core` | yt-dlp、gallery-dl、Trafilatura | 研究、下载、素材归档 |
| `creator` | core + MoneyPrinterTurbo | 主题、文案、素材、配音、字幕到短视频 |
| `full` | creator + NarratoAI + VideoLingo | 影视解说、已有视频分析、翻译和多语言配音 |

预览将执行的命令和锁定版本：

```bash
python scripts/install_web_media_stack.py --profile full --dry-run
```

第三方程序安装到：

```text
tools/web-media/
```

该目录被 `.gitignore` 排除。仓库只保存审核过的仓库地址、提交 SHA、许可证和安装脚本：

```text
tools/web-media-stack.lock.json
```

## 2. API Key

首次安装会从模板创建：

```text
tools/web-media/.env
```

模板文件：

```text
config/web-media.env.example
```

常用字段：

```text
MPT_LLM_PROVIDER=moonshot
MPT_LLM_API_KEY=
MPT_PEXELS_API_KEY=
PEXELS_API_KEY=
PIXABAY_API_KEY=
```

不要把真实密钥提交到 Git、放进视频文案、打印到日志或发送到不受信任服务。

MoneyPrinterTurbo 官方 Skill 会复用现有配置，只在缺少必要凭据时要求一次性补充。

## 3. 创建项目

```bash
python scripts/scaffold_web_media_project.py \
  --name "空间太阳能电站科普" \
  --topic "空间太阳能电站如何向地面输送能量" \
  --duration 90 \
  --aspect-ratio 9:16 \
  --language zh-CN
```

生成目录：

```text
projects/空间太阳能电站科普/
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

`projects/` 默认不提交到 Git，避免把素材、密钥、缓存和大视频推入仓库。

## 4. 搜索开放素材

### Wikimedia Commons

```bash
python scripts/search_open_media.py \
  --provider commons \
  --media-type image \
  --query "space based solar power" \
  --limit 20 \
  --output "projects/空间太阳能电站科普/research/search-results/commons.json"
```

该工具会读取 Commons 的文件页和扩展许可证元数据。仍应人工检查每个文件页面，因为历史上传、署名和衍生作品可能有额外要求。

### Openverse

```bash
python scripts/search_open_media.py \
  --provider openverse \
  --media-type image \
  --query "solar power satellite" \
  --limit 20
```

Openverse 用于发现 Creative Commons 或公共领域图片与音频，最终授权以原始来源页面为准。

### Pexels

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

Pexels API 需要密钥。项目应保留 Pexels 来源链接，并在可能时署名摄影作者。

### Pixabay

```bash
python scripts/search_open_media.py \
  --provider pixabay \
  --media-type video \
  --query "satellite energy" \
  --limit 12 \
  --download-first 3 \
  --download-dir "projects/空间太阳能电站科普/assets/videos" \
  --manifest "projects/空间太阳能电站科普/manifests/assets.jsonl"
```

Pixabay API 需要密钥。脚本会下载候选素材而不是永久热链，并记录内容许可证页面。

## 5. 收集公开网页资料

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/official-document" \
  --project "projects/空间太阳能电站科普" \
  --asset-id "official-source-001" \
  --license "Research reference; quotation limits apply" \
  --rights-status restricted
```

提取后的 Markdown 放进：

```text
research/documents/
```

`restricted` 表示可用于研究和事实核查，但不能把大段正文直接作为视频旁白或画面素材。

## 6. 下载用户已获许可的视频或图片

公开视频：

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

公开图库：

```bash
python scripts/ingest_authorized_source.py \
  --type gallery \
  --url "https://example.com/gallery" \
  --project "projects/项目名称" \
  --asset-id "gallery-001" \
  --license "CC BY 4.0" \
  --license-url "https://creativecommons.org/licenses/by/4.0/" \
  --rights-status cc-by \
  --creator "作者名称" \
  --attribution "作者名称，CC BY 4.0"
```

下载包装器不提供 Cookie、账号密码、浏览器会话或 DRM 绕过参数。

## 7. 素材清单和版权闸门

检查清单：

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

搜索脚本下载的候选素材默认写为：

```json
"selected": false
```

Codex 必须先查看内容、分辨率、相关性、人物隐私和授权，再将选中的素材标记为 `selected=true`。

## 8. 生成文案和成片

### MoneyPrinterTurbo：主题直接生成

在 `skills/moneyprinterturbo-video` 目录中运行：

```bash
uv run --no-project --python 3.11 python mpt_agent.py \
  --subject "空间太阳能电站如何工作"
```

默认生成中文 9:16 视频，使用素材平台画面、Edge TTS、字幕和背景音乐。

### Auto-Editor：指定素材混剪

加载：

```text
skills/ai-video-editing
```

先预览切点，再渲染新文件，不覆盖原素材。需要人工精修时可导出 Premiere、DaVinci Resolve、Final Cut Pro、Shotcut 或 Kdenlive 工程。

### NarratoAI：已有视频解说

完整安装后位于：

```text
tools/web-media/apps/NarratoAI
```

适用于用户自有、公共领域或已获许可的视频分析、解说文案、配音和自动剪辑。

### VideoLingo：翻译和配音

完整安装后位于：

```text
tools/web-media/apps/VideoLingo
```

适用于已有视频的字幕识别、翻译、术语一致性、配音和本地化。

## 9. 给 Codex 的直接指令

```text
加载 skills/web-media-producer。
围绕“空间太阳能电站如何工作”制作 90 秒中文竖屏科普视频。
先创建项目，检索官方文档和可信来源；只下载公共领域、CC、Pexels、Pixabay
或我已授权的素材。所有素材写入 assets.jsonl，并在最终渲染前通过版权校验。
写原创文案和逐镜头分镜，生成配音、字幕和背景音乐。
优先用 MoneyPrinterTurbo 生成基础成片，再用 ai-video-editing 做节奏检查和必要精修。
交付 MP4、SRT、文案、分镜、来源清单和署名清单。
不要覆盖原文件，不要打印 API Key，不要绕过 DRM、登录或付费墙。
```

## 10. 能力边界

这套配置能够广泛搜索和整理公开网络资料，但不能承诺：

- 抓取整个互联网；
- 绕过平台限制、登录、验证码、付费墙或 DRM；
- 自动获得任何第三方视频、图片、音乐或文章的版权；
- 完全无需人工复核字幕、事实、素材许可和最终剪辑；
- 在没有实际运行生成流程时声称成片已完成。

对商用、新闻、医疗、法律、金融、人物声誉和争议内容，应进行更严格的来源和权利审核。
