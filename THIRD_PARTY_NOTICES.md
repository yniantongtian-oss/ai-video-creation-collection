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

## Speech Models

本仓库不托管 Whisper、Parakeet 或其他语音模型权重。用户自行下载模型时，必须分别核对模型权重、数据集、代码和输出的适用条款。
