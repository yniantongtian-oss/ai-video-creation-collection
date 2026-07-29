---
name: ai-video-editing
description: 将已有视频、录屏、口播、播客或 AI 生成镜头转换为可执行的自动剪辑方案，并优先调用仓库内的 auto-editor Skills。适用于删除静音和黑场、依据声音/运动/字幕筛选片段、按台词剪辑、变速、缩放、叠加 Logo、画中画、音量处理、字幕转写，以及导出 Premiere、DaVinci Resolve、Final Cut Pro、Shotcut 或 Kdenlive 工程。先预览剪辑决策，再输出新文件，不覆盖原素材。
metadata:
  version: 1.0.0
  language: zh-CN
---

# AI Video Editing Skill

把“帮我剪一下”转换成 **可预览、可回退、可复现** 的自动剪辑命令。核心执行器是 `auto-editor`；本 Skill 负责理解需求、选择剪辑检测方法、生成安全命令并检查输出。

## 使用前检查

1. 在仓库根目录运行：

```bash
python scripts/install_auto_editor.py
python scripts/check_video_editing_tools.py
```

2. 优先使用仓库下载的可执行文件：

```text
tools/auto-editor/bin/auto-editor
tools/auto-editor/bin/auto-editor.exe
```

若已加入系统 `PATH`，也可直接使用 `auto-editor`。

3. 不使用 `pip install auto-editor`。上游已经停止通过 pip 发布 CLI，应使用官方 Release 二进制、Homebrew 或自行编译。

## 任务路由

根据任务加载对应 Skill：

| 任务 | Skill |
|---|---|
| 删除静音、无动作、黑场；手动裁剪；控制节奏 | `../auto-editor/SKILL.md` |
| 变速、缩放、淡入淡出、音量、Logo、画中画、动画 | `../auto-editor-effects/SKILL.md` |
| 转写字幕、按关键词或台词保留/删除片段 | `../auto-editor-transcribe/SKILL.md` |
| 导出 Premiere、Resolve、Final Cut、Shotcut、Kdenlive 或分镜片段 | `../auto-editor-export/SKILL.md` |

复杂任务可以组合多个 Skill，但必须先完成基础粗剪，再叠加效果和导出。

## 标准执行流程

### 1. 保护原始素材

- 只读取原文件。
- 输出到新的文件名或 `outputs/` 目录。
- 不使用与输入相同的路径。
- 记录输入路径、输出路径、命令、阈值和工具版本。

### 2. 读取媒体信息

```bash
auto-editor info input.mp4
```

确认时长、分辨率、帧率、音轨和字幕轨。多个音轨时，明确选择哪个音轨或使用 `stream=all`。

### 3. 先预览，不直接渲染

```bash
auto-editor input.mp4 --preview
```

任何自动剪辑命令首次运行都先追加 `--preview`。检查预计删除时长、片段数量，以及是否误删句首、句尾或低音量内容。

### 4. 最小粗剪

口播/录屏默认从以下起点测试：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  --preview
```

确认后移除 `--preview` 并指定输出：

```bash
auto-editor input.mp4 \
  --edit audio:threshold=0.04,stream=all \
  --margin 0.25s \
  --smooth 0.2s,0.1s \
  -o outputs/input_cut.mp4
```

阈值不是固定答案。说话较轻时降低阈值；环境噪声较高时提高阈值，并重新预览。

### 5. 组合声音与运动

保留“有声音或有明显运动”的内容：

```bash
auto-editor input.mp4 \
  --edit "(or audio:0.03 motion:0.02)" \
  --margin 0.2s \
  --preview
```

对纯画面演示、游戏录像或无旁白素材，优先采用运动检测；对口播、课程和播客视频，优先采用声音或字幕检测。

### 6. 字幕与按台词剪辑

先生成字幕：

```bash
auto-editor whisper input.mp4 /path/to/ggml-model.bin \
  --format srt \
  -o input.srt
```

保留包含指定词的片段：

```bash
auto-editor input.mp4 --edit word:关键词 --preview
```

删除包含口头禅的片段：

```bash
auto-editor input.mp4 --edit "(not word:嗯)" --preview
```

按词剪辑依赖转写准确度。中文、方言、专有名词和多人重叠说话必须人工复核字幕与切点。

### 7. 效果与包装

静音部分不删除而是加速：

```bash
auto-editor input.mp4 -w:0 speed:6,volume:0.35 -o outputs/input_fast_silence.mp4
```

添加 Logo：

```bash
auto-editor input.mp4 -w:1 add:./assets/logo.png -o outputs/input_logo.mp4
```

轻微动态缩放：

```bash
auto-editor input.mp4 -w:1 zoom:1..1.08:ease=inout -o outputs/input_zoom.mp4
```

效果应服务信息表达。默认不使用高频旋转、过度缩放或影响可读性的动画。

### 8. 导出专业剪辑工程

```bash
auto-editor input.mp4 --export premiere
auto-editor input.mp4 --export resolve
auto-editor input.mp4 --export final-cut-pro
auto-editor input.mp4 --export shotcut
auto-editor input.mp4 --export kdenlive
```

需要把自动切点交给剪辑师继续精修时，优先导出工程或 `clip-sequence`，而不是只交付压制后的成片。

## 常用成品配方

### 口播视频紧凑粗剪

```bash
auto-editor talk.mp4 \
  --edit audio:-30dB \
  --margin 0.25s \
  --smooth 0.18s,0.12s \
  -anorm ebu \
  -o outputs/talk_cut.mp4
```

### 课程录屏保留讲解与操作

```bash
auto-editor lesson.mp4 \
  --edit "(or audio:0.025 motion:0.015)" \
  --margin 0.3s \
  -o outputs/lesson_cut.mp4
```

### 播客删除长停顿并略微加速说话

```bash
auto-editor podcast.mp3 \
  -w:0 cut \
  -w:1 speed:1.08 \
  -anorm ebu \
  -o outputs/podcast_tight.m4a
```

### 先自动粗剪，再进入 DaVinci Resolve

```bash
auto-editor interview.mp4 \
  --edit audio:-28dB \
  --margin 0.3s \
  --export resolve \
  -o outputs/interview.fcpxml
```

## 验收标准

- 原始文件未被覆盖。
- 句首、句尾没有被明显截断。
- 没有删除必要的无声画面、字幕卡、停顿表情或操作过程。
- 音画同步，时长与帧率符合交付要求。
- 字幕时间轴和文字经过抽检。
- 工程导出可被目标剪辑软件打开。
- 输出命令、工具版本和关键阈值已经记录。

## 失败回退

- 误删说话：降低声音阈值，增大 `--margin`，或改用字幕检测。
- 保留噪声过多：提高阈值，指定正确音轨，或先做降噪。
- 切点过碎：增大 `--smooth` 的最小剪切/保留时长。
- 无声但重要的画面被删：组合 motion，或使用 `--keep` 强制保留时间段。
- 自动效果不满意：导出专业剪辑工程，保留自动切点后人工精修。

## 边界与许可

- 上游 Skill 文本来自 `WyattBlue/auto-editor`，其代码和 Skill 采用 Unlicense/公共领域声明；详细记录见仓库 `THIRD_PARTY_NOTICES.md`。
- 官方 Release 二进制可能包含具有各自许可证的组件；下载和使用前查看对应 Release 与上游说明。
- 不将自动剪辑描述为“完全无需人工检查”。涉及字幕、人物身份、商业发布和关键内容时必须复核。
