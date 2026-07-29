---
name: moneyprinterturbo-video
description: 使用 MoneyPrinterTurbo 从主题、标题、想法、提示词或脚本直接生成完整视频。适用于中文短视频、知识科普、营销、口播旁白和社交媒体视频，也适用于安装或配置 MoneyPrinterTurbo、识别缺少的 API Key、修复生成失败、查找最终 MP4。预期结果必须是成片，而不是只给安装说明。
compatibility: 需要可使用终端、网络、文件系统和长时间前台命令的 Agent。上游官方 Skill 明确支持 macOS 和 Windows，并要求使用 uv。
metadata:
  author: "harry0703@hotmail.com"
  upstream_version: "1.3.2"
  upstream: "https://github.com/harry0703/MoneyPrinterTurbo"
  upstream_commit: "42f776e2e0950394ea150f28e4ab49d8ab9b3ba1"
  local_wrapper_version: "1.0.0"
---

# MoneyPrinterTurbo 成片生成

用户只需提供视频主题或脚本。Agent 应完成安装、复用现有配置、生成、等待任务结束并交付最终 MP4，不要停在命令说明阶段。

本目录的 `mpt_agent.py` 是安全引导器：它会下载经过审核并锁定 Git blob SHA 的官方上游助手脚本，再原样执行。不得绕过完整性校验，也不得改为下载上游 `main` 的未固定版本。

## 必须遵守

1. 只在 API 凭据缺失、被拒绝或不可用时询问用户，并把所有缺失凭据合并成一次询问。
2. 不要在标准生成任务中反复询问是否继续，也不要只输出一堆安装命令。
3. 使用一个前台命令完成安装与生成，终端超时应至少为 20 分钟。
4. 不用 `sleep`、`ps`、重复 `ls` 或重复读取日志轮询。终端返回可恢复会话时，应继续等待同一会话。
5. 永远不要打印 API Key、Token、完整 `config.toml` 或包含凭据的配置片段。
6. 成功时只依据助手输出的 `MPT_RESULT` 和 `VIDEO_FILE` 交付结果；失败时只读取助手报告的短错误或日志尾部。

## 默认成片

用户未指定时，生成一条中文 `9:16` 竖屏视频：

- 使用 Pexels 授权素材；
- 默认中文 Edge TTS 音色；
- 自动字幕；
- 背景音乐；
- 安装目录为用户主目录下的 `MoneyPrinterTurbo`。

## 执行方式

把终端工作目录设置为本 Skill 目录，然后运行相对路径命令：

```bash
uv run --no-project --python 3.11 python mpt_agent.py --subject "<视频主题>"
```

不要先运行额外的 `uv --version` 探测。只有终端明确提示 `uv` 不存在时，才安装 uv 并重试一次。

macOS / Linux 的 uv 官方安装命令：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

上游官方 Skill 将标准执行范围限定为 macOS 和 Windows。Linux 环境应优先使用本仓库的 `scripts/install_web_media_stack.py --profile creator` 安装 MoneyPrinterTurbo，再依据其官方 CLI 文档运行；不要未经验证地声称官方 Skill 在 Linux 已通过测试。

## 附加要求

额外视频参数放在 `--` 后面，例如：

```bash
uv run --no-project --python 3.11 python mpt_agent.py \
  --subject "空间太阳能电站如何工作" \
  -- \
  --video-aspect portrait \
  --video-source pexels
```

遇到陌生参数时，只运行一次上游 `cli.py --help` 核对，不要猜测参数名。

## 返回码处理

### 返回码 0：交付成片

成功输出格式：

```text
MPT_RESULT
VIDEO_FILE=<绝对路径>/final-1.mp4
TASK_DIR=<绝对路径>/storage/tasks/<task_id>
LOG_FILE=<绝对路径>/run-<task_id>.log
RESULT_FILE=<绝对路径>/latest-result.json
```

助手只有在确认 MP4 存在且非空后才输出 `VIDEO_FILE`，无需再运行 `ls` 或 `stat`。

如果终端显示退出码 0，但输出被截断且看不到 `MPT_RESULT`，只读取一次：

```text
~/MoneyPrinterTurbo/.agent-logs/moneyprinterturbo-video/latest-result.json
```

`status=completed` 即为成功。

### 返回码 10：一次性询问凭据

助手会输出 `MPT_NEEDS_INPUT`，并列出实际缺失字段。只询问列出的值，不要重复索取已有配置。可能的环境变量包括：

```text
MPT_LLM_PROVIDER
MPT_LLM_API_KEY
MPT_LLM_BASE_URL
MPT_LLM_MODEL_NAME
MPT_PEXELS_API_KEY
```

用户提供后，仅把所需值作为本次命令的环境变量传入，然后重跑原命令。不要把密钥写进聊天内容、日志或 Git。

### 返回码 1：修复或报告

根据 `MPT_ERROR` 和 `LOG_FILE` 修复可恢复问题并重试一次。只有确实需要新 API Key 时才询问用户。再次失败后，应报告失败阶段、简短错误和日志路径。

## 与全网素材项目结合

当用户不仅要“主题生成视频”，还要求查阅文档、指定来源、保留出处或混合自有素材时，先加载 `../web-media-producer/SKILL.md`：

1. 建立研究项目和素材清单；
2. 收集开放授权或用户已获许可的资料；
3. 完成事实核查、文案和镜头表；
4. 再把最终文案或主题交给本 Skill 生成成片；
5. 把 MoneyPrinterTurbo 返回的任务目录和素材来源信息并入项目交付。

不得把“能下载”视为“有权使用”。最终发布前仍需检查素材平台条款、作者署名、音乐许可、事实准确性和平台规则。
