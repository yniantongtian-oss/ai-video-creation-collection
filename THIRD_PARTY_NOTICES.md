# Third-Party Notices

本文件记录直接复制、适配或通过脚本下载的第三方内容。仓库根目录的 MIT 许可证只适用于本仓库原创部分，不会改变第三方项目、模型权重、二进制组件或素材的许可证。

## Auto-Editor Agent Skills

- 上游项目：`WyattBlue/auto-editor`
- 上游地址：<https://github.com/WyattBlue/auto-editor>
- 导入日期：2026-07-29
- 上游许可证：Unlicense / public-domain dedication
- 上游许可证文件：<https://github.com/WyattBlue/auto-editor/blob/master/LICENSE>

导入文件：

| 本仓库文件 | 上游文件 | 导入时上游 blob SHA |
|---|---|---|
| `skills/auto-editor/SKILL.md` | `skills/auto-editor/SKILL.md` | `0b23e0d1b7e6268d45f40c528dc9c684cf5bf501` |
| `skills/auto-editor-effects/SKILL.md` | `skills/auto-editor-effects/SKILL.md` | `2bc16875a5f9321e948049726e2e2b44cefd0d08` |
| `skills/auto-editor-export/SKILL.md` | `skills/auto-editor-export/SKILL.md` | `cb99014f41ccab06875bb067b3ab102bd20c5e40` |
| `skills/auto-editor-transcribe/SKILL.md` | `skills/auto-editor-transcribe/SKILL.md` | `830259ec762c091be35ad313fcf4d4803e5d2dcf` |

上游许可证声明允许复制、修改、发布、使用、编译、销售和分发软件，并按“原样”提供，不附带任何明示或暗示担保。完整法律文本以该项目的 `LICENSE` 文件为准。

## Auto-Editor Release Binaries

`scripts/install_auto_editor.py` 不在本仓库中托管二进制。脚本运行时会从以下官方 GitHub Releases 获取当前系统对应的资产：

- <https://github.com/WyattBlue/auto-editor/releases>

官方构建目前提供的主要资产名称包括：

```text
auto-editor-linux-x86_64
auto-editor-linux-aarch64
auto-editor-linux-armv7
auto-editor-macos-x86_64
auto-editor-macos-arm64
auto-editor-windows-x86_64.exe
auto-editor-windows-aarch64.exe
```

Release 二进制可能包含 FFmpeg、编解码器、语音转写组件或其他采用各自许可证的依赖。使用者应查看所下载版本的 Release 说明、构建配置和许可证信息。下载脚本记录来源版本与资产 URL，但不能替代数字签名或独立供应链审计。

## MoneyPrinterTurbo Agent Skill

- 上游项目：`harry0703/MoneyPrinterTurbo`
- 上游地址：<https://github.com/harry0703/MoneyPrinterTurbo>
- 审核提交：`42f776e2e0950394ea150f28e4ab49d8ab9b3ba1`
- 上游许可证：MIT
- 上游 Skill：`docs/skill/SKILL.md`
- 上游 Skill blob SHA：`a94218f1df77c7ae8ec3d5bc5c07c99618219e7e`
- 上游助手：`docs/skill/mpt_agent.py`
- 上游助手 blob SHA：`e51245ae7a1c263b88ca5b3cd76aa6a1896093a6`

本仓库的 `skills/moneyprinterturbo-video/SKILL.md` 根据上游官方 Skill 进行中文适配，并增加了本仓库素材版权闸门和 Linux 能力边界说明。

本仓库不直接复制上游完整助手脚本。`skills/moneyprinterturbo-video/mpt_agent.py` 是本仓库原创的最小引导器，会从固定提交下载官方助手，并按照 Git blob SHA-1 校验内容后执行。更新提交和 SHA 前必须重新审查上游代码。

## Web Media Stack External Dependencies

`scripts/install_web_media_stack.py` 根据 `tools/web-media-stack.lock.json` 把第三方工具安装或克隆到被 Git 忽略的 `tools/web-media/`。这些项目不属于本仓库 MIT 许可证。

| 项目 | 锁定提交 | 许可证 | 用途 |
|---|---|---|---|
| `yt-dlp/yt-dlp` | `fdcc954df4955267ec1627cbeb347b661a110e7c` | Unlicense | 公开或已授权视频、音频、字幕与元数据下载 |
| `mikf/gallery-dl` | `8939a870a1b319634489839a8b224803dccb13ec` | GPL-2.0 | 公开或已授权图片图库下载；作为外部命令使用 |
| `adbar/trafilatura` | `467fdb3829a869c018834d7b02f790980dda263c` | Apache-2.0 | 网页正文和元数据提取 |
| `harry0703/MoneyPrinterTurbo` | `42f776e2e0950394ea150f28e4ab49d8ab9b3ba1` | MIT | 文案、授权素材、配音、字幕、音乐与短视频合成 |
| `linyqh/NarratoAI` | `a9e17d0e36171ab604433abafd127f78eefbf350` | MIT | 已有视频理解、解说文案与自动剪辑 |
| `Huanshere/VideoLingo` | `968268bbcec63c3dac332c698e81c302abdea6c2` | Apache-2.0 | 视频翻译、字幕、本地化与配音 |

安装器不会自动接受第三方许可证、API 条款或模型条款。运行前应查看锁定提交中的许可证和文档。第三方应用可能继续下载 Python 包、模型、FFmpeg、语音组件或前端依赖，这些依赖具有各自许可证。

## Stock and Open Media Providers

`scripts/search_open_media.py` 可以调用 Wikimedia Commons、Openverse、Pexels 和 Pixabay API。搜索结果中的许可证信息只是初步元数据；最终使用应打开原始来源页面核验。

- Wikimedia Commons 文件可能要求署名、相同方式共享或遵守页面上的额外说明。
- Openverse 是发现入口，实际许可证和文件状态以原始托管来源为准。
- Pexels 内容受 Pexels License 和 API 条款约束，并鼓励链接和作者署名。
- Pixabay 内容受 Pixabay Content License 和 API 条款约束，API 结果展示和批量下载受限制。

本仓库不授予任何第三方素材的版权，也不保证素材一定适合商用、广告、人物肖像、商标或敏感场景。

## Speech Models

本仓库不托管 Whisper、WhisperX、Parakeet、GPT-SoVITS、IndexTTS 或其他语音模型权重。用户自行下载模型时，必须分别核对模型权重、数据集、代码、音色克隆授权和输出的适用条款。
