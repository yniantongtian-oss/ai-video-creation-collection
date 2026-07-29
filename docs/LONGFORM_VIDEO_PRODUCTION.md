# 60–360 分钟长篇视频制作指南

本指南用于制作一小时以上的纪录片、科普、课程、历史叙事、调查解释、专题评论和多章节视频。

长视频不能按短视频方式一次生成。正确方法是：**分章研究、分章写稿、分章配音、分章渲染，最后拼接**。

## 1. 为什么必须分章

一条 90 分钟中文视频，按每分钟约 260 个中文字符计算，旁白约 23,400 字符；按每 10 秒更换一次主要视觉内容计算，约需要 540 个镜头段。实际项目还会包含：

- 数十至数百份文档；
- 数百至上千个候选图片、视频和音频；
- 数百条事实与来源标记；
- 多次模型请求；
- 多段配音和字幕；
- 大量中间视频缓存；
- 数十 GiB 的临时文件。

因此本仓库默认把 90 分钟视频拆成约 13 章，每章约 7 分钟。任何一章失败，只重跑该章。

## 2. 安装

先安装网络研究与素材工具：

```bash
python scripts/install_web_media_stack.py --profile full
```

安装长视频专用运行环境：

```bash
python scripts/install_longform_stack.py
```

安装 Auto-Editor：

```bash
python scripts/install_auto_editor.py
```

只查看安装计划：

```bash
python scripts/install_longform_stack.py --dry-run
```

长视频运行环境安装到：

```text
tools/longform/.venv
```

本地配置文件：

```text
tools/longform/.env
```

该目录和密钥不会进入 Git。

## 3. 配置大模型

编辑：

```text
tools/longform/.env
```

至少填写一个 OpenAI-compatible Chat Completions 服务：

```text
LONGFORM_LLM_BASE_URL=https://你的服务地址/v1
LONGFORM_LLM_API_KEY=你的密钥
LONGFORM_LLM_MODEL=你的模型名称
```

长篇项目应选择：

- 能稳定输出结构化 JSON 的模型；
- 具有足够上下文长度；
- 中文长文能力较强；
- 支持较高单次输出长度；
- 费用和速率限制可控。

密钥不能写进项目文案、日志、README 或提交记录。

## 4. 创建项目

90 分钟横屏纪录片：

```bash
python scripts/scaffold_longform_project.py \
  --name "空间太阳能电站完整纪录片" \
  --topic "空间太阳能电站的历史、原理、工程方案、争议与未来" \
  --duration 90 \
  --chapter-minutes 7 \
  --aspect-ratio 16:9 \
  --audience "对科技感兴趣的大众观众" \
  --style "纪录片式科普，信息密度高但表达自然"
```

两小时项目：

```bash
python scripts/scaffold_longform_project.py \
  --name "两小时专题" \
  --topic "专题主题" \
  --duration 120 \
  --chapter-minutes 8 \
  --aspect-ratio 16:9
```

项目目录结构：

```text
projects/<项目名称>/
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
│   ├── outline.json
│   └── chapter-map.csv
├── assets/
├── manifests/
│   ├── assets.jsonl
│   ├── facts.jsonl
│   └── render.jsonl
├── chapters/
│   ├── 01/
│   ├── 02/
│   └── ...
├── state/
├── logs/
└── outputs/
```

## 5. 准备研究资料

把以下内容放进：

```text
projects/<项目名称>/research/inbox/
```

支持：

- PDF；
- DOCX；
- PPTX；
- TXT、Markdown；
- HTML；
- CSV、TSV、JSON；
- SRT、VTT 字幕；
- 网页提取后的文档。

建议资料组合：

- 官方机构文档；
- 原始论文和技术报告；
- 法律、政策和标准文件；
- 博物馆、档案馆和大学资料；
- 可信新闻机构的背景报道；
- 专家演讲或采访字幕；
- 用户自己的笔记、提纲和历史资料；
- 反方观点和争议来源。

不要只收集支持单一结论的资料。

### 网页资料

可先使用现有工具提取：

```bash
python scripts/ingest_authorized_source.py \
  --type document \
  --url "https://example.com/article" \
  --project "projects/<项目名称>" \
  --asset-id "source-example" \
  --license "reference-only" \
  --rights-status restricted
```

研究引用权和媒体再利用权是两件事。网页可以用于事实研究，不代表网页中的图片或视频可以直接进入成片。

## 6. 建立语料库

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<项目名称>"
```

指定额外资料目录：

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<项目名称>" \
  --input "/path/to/documents" \
  --input "/path/to/subtitles"
```

重新建立索引：

```bash
python scripts/ingest_longform_corpus.py \
  --project "projects/<项目名称>" \
  --reset-index
```

脚本会：

1. 计算 SHA-256；
2. 跳过重复文件；
3. PDF 按页保留定位；
4. PPTX 按幻灯片保留定位；
5. 提取正文；
6. 按约 2,200 字符切块并保留重叠上下文；
7. 写入 JSONL；
8. 建立 SQLite 全文检索索引。

扫描版 PDF 无可提取文字时，需要先进行 OCR。不要假装已经读取空白页面。

## 7. 生成研究摘要、大纲、长文案和镜头表

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  research
```

处理顺序：

```text
逐来源摘要
→ 全片章节大纲
→ 每章独立检索相关资料
→ 每章独立写稿
→ 每章独立生成镜头表
```

主要产物：

```text
research/summaries/*.md
outline/outline.json
outline/chapter-map.csv
chapters/*/script.md
chapters/*/narration.txt
chapters/*/claims.json
chapters/*/open-questions.json
chapters/*/shots.json
```

`script.md` 会保留：

```text
[S:source-id#page=12;chunk=3]
```

`narration.txt` 则是不朗读来源标记的旁白稿。

### 只重写某一章

```bash
python scripts/longform_pipeline.py \
  --project "projects/<项目名称>" \
  write \
  --chapter 4 \
  --force
```

重新生成该章镜头表：

```bash
python scripts/longform_pipeline.py \
  --project "projects/<项目名称>" \
  shots \
  --chapter 4 \
  --force
```

## 8. 素材规模规划

按每 10 秒更换一次主要画面估算：

| 成片时长 | 视觉段落 | 建议独立素材数 |
|---|---:|---:|
| 60 分钟 | 约 360 | 120–220 |
| 90 分钟 | 约 540 | 180–320 |
| 120 分钟 | 约 720 | 240–420 |
| 180 分钟 | 约 1,080 | 350–600 |

一个素材可以经过不同裁切、轻微推拉、局部放大、字幕叠加、地图标注和时间线包装后合理复用，但不能连续长时间重复。

每章建议至少包含：

- 3–8 个视频 B-roll；
- 5–15 张档案、照片、地图、文档页或示意图；
- 必要的数据图和时间线；
- 章节标题卡；
- 1–2 个视觉记忆点。

## 9. 生成素材搜索计划

```bash
python scripts/build_longform_asset_plan.py \
  --project "projects/<项目名称>"
```

默认会把数百个镜头查询去重为每章约 12 个搜索组。

执行开放素材搜索：

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  assets \
  --execute-search \
  --download-first 1
```

`--download-first 1` 表示每个平台、每个查询先下载一个候选，避免一次下载几千个文件。

需要增加候选：

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  assets \
  --execute-search \
  --download-first 3 \
  --search-limit 12
```

来源包括：

- Wikimedia Commons；
- Openverse；
- Pexels；
- Pixabay。

自动下载内容全部为候选，默认不能进入成片。

## 10. 添加用户自己的素材

```bash
python scripts/media_asset_manifest.py add \
  --manifest "projects/<项目名称>/manifests/assets.jsonl" \
  --id "my-interview-001" \
  --kind video \
  --local-path "assets/global/videos/interview.mp4" \
  --license "User owned" \
  --rights-status user-owned \
  --permission-note "由项目成员拍摄，受访者已同意用于本视频" \
  --title "专家采访"
```

用户自有素材必须写清楚所有权或授权说明。

## 11. 审核并批准候选素材

列出候选：

```bash
python scripts/media_asset_manifest.py list \
  --manifest "projects/<项目名称>/manifests/assets.jsonl" \
  --candidates
```

批准：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<项目名称>/manifests/assets.jsonl" \
  --id "asset-id" \
  --value true \
  --note "已核对内容、来源页、许可证和署名要求"
```

批量批准：

```bash
python scripts/media_asset_manifest.py set-selected \
  --manifest "projects/<项目名称>/manifests/assets.jsonl" \
  --ids-file approved-assets.txt \
  --value true
```

批准动作会检查：

- 文件存在；
- SHA-256 未变化；
- 许可证允许；
- 非本地素材具有 HTTPS 来源页；
- CC BY / CC BY-SA 包含作者和许可证地址；
- 用户自有或单独授权素材包含许可说明。

## 12. 配音

```bash
python scripts/render_longform_narration.py \
  --project "projects/<项目名称>"
```

默认使用：

```text
zh-CN-XiaoxiaoNeural
```

修改音色：

```bash
python scripts/render_longform_narration.py \
  --project "projects/<项目名称>" \
  --voice zh-CN-YunxiNeural
```

只重做第四章：

```bash
python scripts/render_longform_narration.py \
  --project "projects/<项目名称>" \
  --chapter 4 \
  --force
```

每章文案会自动拆成多个配音片段，并生成对应字幕。失败时只重试失败片段。

## 13. 构建时间线

```bash
python scripts/build_longform_timeline.py \
  --project "projects/<项目名称>"
```

脚本只使用已经批准的图片和视频素材，并根据：

- 镜头检索词；
- 旁白关键词；
- 素材标题和说明；
- 素材类型；
- 所属章节；
- 最近使用次数；

自动匹配素材。

素材不足时默认失败。只有内部预览可以显式使用：

```bash
python scripts/build_longform_timeline.py \
  --project "projects/<项目名称>" \
  --allow-placeholders
```

占位镜头不能进入最终发布版。

## 14. 分章渲染

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<项目名称>"
```

流程：

```text
每个镜头转为统一规格缓存
→ 镜头无损拼接成章节画面
→ 混合旁白和可选背景音乐
→ 写入字幕轨
→ 输出章节 MP4
```

只重做第四章：

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<项目名称>" \
  --chapter 4 \
  --force
```

烧录字幕：

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<项目名称>" \
  --burn-subtitles
```

指定背景音乐：

```bash
python scripts/render_longform_chapters.py \
  --project "projects/<项目名称>" \
  --bgm "/path/to/licensed-bgm.mp3"
```

背景音乐也必须具有清晰授权。

## 15. 最终拼接

```bash
python scripts/assemble_longform_video.py \
  --project "projects/<项目名称>"
```

输出：

```text
outputs/final/<项目名称>.mp4
outputs/final/full.srt
outputs/final/youtube-chapters.txt
outputs/final/chapters.ffmetadata
outputs/final/assembly-report.json
```

默认优先使用无损流复制拼接。如果章节参数不一致，则自动回退到重编码。

## 16. 一条命令生产

素材已经审核批准后：

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  produce
```

它会执行：

```text
版权和资源预检
→ 分章配音
→ 分章时间线
→ 分章渲染
→ 最终拼接
```

素材未审核时会停止并返回：

```text
LONGFORM_NEEDS_ASSET_REVIEW
```

这是正常的安全闸门，不是程序故障。

## 17. 从头执行

资料已放入 `research/inbox/` 后：

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  all \
  --execute-search \
  --download-first 1
```

该命令会在素材审核闸门处停止。审核并批准素材后运行：

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  produce
```

## 18. 状态与断点

```bash
python scripts/run_longform_project.py \
  --project "projects/<项目名称>" \
  status
```

状态文件：

```text
state/pipeline.json
chapters/<编号>/status.json
```

默认跳过已经存在且有效的：

- 来源摘要；
- 大纲；
- 章节文案；
- 镜头表；
- 配音片段；
- 镜头缓存；
- 章节视频；
- 最终成片。

不要随意使用 `--force`。

## 19. 预检

开始研究前：

```bash
python scripts/longform_preflight.py \
  --project "projects/<项目名称>" \
  --stage setup
```

渲染前：

```bash
python scripts/longform_preflight.py \
  --project "projects/<项目名称>" \
  --stage render
```

最终拼接前：

```bash
python scripts/longform_preflight.py \
  --project "projects/<项目名称>" \
  --stage final
```

预检会估算：

- 最终文件大小；
- 推荐临时空间；
- 当前可用磁盘；
- 文案和镜头完整度；
- 素材许可证；
- 占位镜头；
- 配音和章节时长；
- 已渲染章节数量。

## 20. 硬盘与性能建议

90 分钟、8 Mbps 视频加 192 kbps 音频，最终 MP4 通常约数 GiB；考虑原始素材、镜头缓存、章节成片和失败重试，建议至少预留最终文件预计大小的 4–5 倍，再额外预留模型和素材空间。

建议：

- 项目放在 SSD；
- 原始素材和项目缓存分盘；
- 1080p 项目先使用 `medium` 或 `fast` 预设；
- 先渲染一章验证风格和参数；
- 最终确认后再批量渲染所有章节；
- 不建议在 Git 仓库存储视频和音频；
- 重要项目定期备份 `project.json`、研究资料、文案、镜头表和素材清单。

## 21. 质量验收

最终发布前至少检查：

1. 总时长符合要求；
2. 章节顺序和转场正确；
3. 文案无明显重复；
4. 所有关键事实有来源；
5. `NEEDS_SOURCE` 已处理；
6. 人名、时间、地点、数字和引语已复核；
7. 画面与旁白语义匹配；
8. 无错误人物、地点、年代或设备；
9. 无未批准和来源不明素材；
10. CC 署名完整；
11. 无长时间黑屏、静帧和重复画面；
12. 配音音量统一；
13. 背景音乐不遮盖旁白；
14. 字幕无明显断句和时间错位；
15. 章节时间戳正确；
16. `assembly-report.json` 时长检查通过；
17. 抽查开头、中段、结尾和每章交界；
18. 上传前再核对平台规则和商业授权。

## 22. 推荐给 Codex 的完整指令

```text
加载 skills/longform-documentary-producer。

围绕“<主题>”制作一部 90 分钟中文 16:9 长篇纪录片。
先建立长视频项目，读取 research/inbox 中全部资料，建立带 SHA-256、页码和幻灯片定位的语料库。
逐来源摘要后设计约 13 章的大纲，再逐章检索、逐章写稿、逐章生成镜头表。
关键事实必须保留来源标记，资料不足写 NEEDS_SOURCE，不得猜测。

从 Wikimedia Commons、Openverse、Pexels、Pixabay 和用户自有素材中寻找图片、视频和音频。
自动下载内容只能作为候选，必须查看内容、来源页和许可证后才能标记 selected=true。
来源不明、restricted 或 unknown 素材不得进入成片。

审核完成后逐章生成配音和字幕，逐章匹配素材并渲染；一章失败只重跑该章。
最终拼接完整 MP4，生成 full.srt、YouTube 章节时间戳、章节元数据、文案、镜头表、事实清单、素材许可清单和 assembly-report.json。
没有实际生成最终 MP4 时，不得声称成片已完成。
```
