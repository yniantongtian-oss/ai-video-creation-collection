# AI 自动剪辑安装与使用

本仓库已经加入一套基于 **Auto-Editor** 的可执行视频剪辑能力。它适合处理 AI 生成镜头、口播、课程录屏、采访、播客和游戏录像，能够完成自动删除静音、按运动筛选、黑场处理、字幕转写、按台词剪辑、变速与叠加效果，并可导出到专业剪辑软件继续精修。

## 已加入的 Skills

```text
skills/ai-video-editing/        中文统一入口与任务路由
skills/auto-editor/             静音、运动、黑场、手动区间与基础渲染
skills/auto-editor-effects/     变速、音量、缩放、叠加、画中画与动画
skills/auto-editor-transcribe/  Whisper/Parakeet 转写与按台词剪辑
skills/auto-editor-export/      Premiere、Resolve、Final Cut、Shotcut、Kdenlive 导出
```

支持 Agent Skills 的工具可以直接加载上述目录。处理普通中文需求时，优先加载 `skills/ai-video-editing`，它会再路由到对应的上游 Skill。

## 1. 下载官方 Auto-Editor

安装脚本只使用 Python 标准库，会根据当前操作系统和 CPU 架构选择官方 GitHub Release 二进制：

```bash
python scripts/install_auto_editor.py
```

默认安装到：

```text
tools/auto-editor/bin/auto-editor
tools/auto-editor/bin/auto-editor.exe
```

先检查下载计划但不下载：

```bash
python scripts/install_auto_editor.py --dry-run
```

安装指定上游版本：

```bash
python scripts/install_auto_editor.py --version 30.3.0
```

替换已存在的本地二进制：

```bash
python scripts/install_auto_editor.py --force
```

下载完成后，脚本会执行 `--help` 做启动验证，并把来源、版本、资产名称与下载地址记录到本地 `tools/auto-editor/install.json`。二进制和安装记录已被 `.gitignore` 排除，不会进入 Git 历史。

> Auto-Editor CLI 已停止通过 pip 发布。不要把 `pip install auto-editor` 写进新的安装流程。上游推荐使用官方 Release 二进制、Homebrew 或源码编译。

## 2. 检查环境

```bash
python scripts/check_video_editing_tools.py
```

机器可读输出：

```bash
python scripts/check_video_editing_tools.py --json
```

`auto-editor` 是必需项。系统级 `ffmpeg` 与 `ffprobe` 是可选辅助工具；官方 Auto-Editor 二进制已经包含其运行所需的媒体组件。

## 3. 调用仓库内二进制

### Windows PowerShell

```powershell
$AE = ".\tools\auto-editor\bin\auto-editor.exe"
& $AE --help
```

### macOS / Linux

```bash
AE=./tools/auto-editor/bin/auto-editor
"$AE" --help
```

也可以把该目录加入 `PATH`，然后直接运行 `auto-editor`。安装脚本不会自动修改系统 `PATH`。

## 4. 第一次自动粗剪

先查看媒体信息：

```bash
auto-editor info input.mp4
```

第一次必须预览剪辑决策：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

确认没有误删句首、句尾和必要停顿后再渲染：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  -o outputs/input_cut.mp4
```

仓库已忽略 `outputs/` 和常见视频格式，避免误把大文件提交到 Git。

## 5. 常用方法

### 删除静音

```bash
auto-editor talk.mp4 --edit audio:-30dB --margin 0.25s --preview
```

### 保留有声音或有动作的片段

```bash
auto-editor demo.mp4 --edit "(or audio:0.03 motion:0.02)" --preview
```

### 不删除静音，而是加速静音部分

```bash
auto-editor lesson.mp4 -w:0 speed:6,volume:0.35 -o outputs/lesson_fast.mp4
```

### 添加 Logo

```bash
auto-editor input.mp4 -w:1 add:./assets/logo.png -o outputs/input_logo.mp4
```

### 轻微动态缩放

```bash
auto-editor input.mp4 -w:1 zoom:1..1.08:ease=inout -o outputs/input_zoom.mp4
```

### 导出到 DaVinci Resolve

```bash
auto-editor interview.mp4 --edit audio:-28dB --margin 0.3s --export resolve
```

其他导出目标包括：

```text
premiere
resolve
final-cut-pro
shotcut
kdenlive
clip-sequence
v1 / v2 / v3
```

## 6. 字幕转写与按台词剪辑

Auto-Editor 可以调用 Whisper、Parakeet 或受支持的 Apple Speech 后端。模型权重较大且许可证各不相同，本仓库不会自动提交或托管这些权重。

生成 SRT：

```bash
auto-editor whisper input.mp4 /path/to/ggml-model.bin \
  --format srt \
  -o input.srt
```

保留说到某个词的片段：

```bash
auto-editor input.mp4 --edit word:关键词 --preview
```

删除包含某个口头禅的片段：

```bash
auto-editor input.mp4 --edit "(not word:嗯)" --preview
```

中文、方言、专有名词、多人重叠说话和背景音乐会影响转写准确度。按台词剪辑必须抽查字幕和切点。

## 7. 让 AI 使用这套能力

可以直接向支持 Agent Skills 的助手表达目标，例如：

```text
加载 skills/ai-video-editing。先分析 input.mp4，预览删除静音的结果；
不要覆盖原文件，把确认后的成片输出到 outputs/input_cut.mp4，
同时导出一份 DaVinci Resolve 工程。
```

AI 应遵守以下顺序：

```text
读取素材信息 → 选择检测方式 → 生成预览命令 → 检查切点
→ 渲染新文件 → 检查输出 → 按需导出工程
```

不得在没有实际运行结果时声称视频已经剪辑完成。

## 8. 更新 Auto-Editor

查看将要下载的最新版本：

```bash
python scripts/install_auto_editor.py --dry-run
```

更新并重新验证：

```bash
python scripts/install_auto_editor.py --force
python scripts/check_video_editing_tools.py
```

升级后先用短素材验证常用命令。Auto-Editor 的参数、导出格式和组件行为可能随上游版本变化。

## 9. 许可与安全

- 导入的四个上游 Skill 来自 `WyattBlue/auto-editor`，上游声明为 Unlicense/公共领域。
- 官方 Release 二进制可能捆绑采用不同许可证的媒体组件；以对应 Release 和上游文件为准。
- 详细来源和文件版本见根目录 `THIRD_PARTY_NOTICES.md`。
- 不覆盖原素材，不自动发布成片，不对字幕和自动切点做未经验证的准确性承诺。
