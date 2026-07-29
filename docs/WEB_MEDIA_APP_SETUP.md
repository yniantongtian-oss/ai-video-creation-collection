# 重型视频应用配置

`scripts/install_web_media_stack.py` 负责把第三方工具按锁定提交下载到 `tools/web-media/`。MoneyPrinterTurbo、NarratoAI 和 VideoLingo 的 Python 依赖可能很大，因此运行时配置由独立脚本完成：

```bash
python scripts/configure_web_media_apps.py --app all
```

先预览，不修改文件：

```bash
python scripts/configure_web_media_apps.py --app all --dry-run
```

## 单独配置

### MoneyPrinterTurbo

```bash
python scripts/install_web_media_stack.py --profile creator
python scripts/configure_web_media_apps.py --app moneyprinterturbo
```

配置器会：

1. 核对本地 Git HEAD 是否等于 `tools/web-media-stack.lock.json` 中的锁定提交；
2. 运行 `uv sync --frozen`；
3. 若不存在 `config.toml`，从 `config.example.toml` 创建；
4. 不写入或打印任何 API Key。

随后可直接加载：

```text
skills/moneyprinterturbo-video
```

官方 Agent Skill 会在实际生成时识别缺失的 LLM 与 Pexels 凭据，并只请求必要字段。

### NarratoAI

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/configure_web_media_apps.py --app narratoai
```

配置器会运行官方本地流程：

```bash
uv sync
```

并从 `config.example.toml` 创建本地 `config.toml`。编辑配置后启动：

```bash
cd tools/web-media/apps/NarratoAI
uv run streamlit run webui.py --server.maxUploadSize=2048
```

浏览器访问：

```text
http://127.0.0.1:8501
```

### VideoLingo

```bash
python scripts/install_web_media_stack.py --profile full
python scripts/configure_web_media_apps.py --app videolingo
```

配置器调用锁定版本提供的官方安装器：

```bash
python setup_env.py --yes --skip-demucs
```

默认跳过可选的 Demucs，以降低首次安装体积。需要人声分离时：

```bash
python scripts/configure_web_media_apps.py \
  --app videolingo \
  --include-demucs
```

Windows 启动：

```text
OneKeyStart.bat
```

macOS / Linux 启动：

```bash
cd tools/web-media/apps/VideoLingo
.venv/bin/streamlit run st.py
```

## 配置安全

- 第三方应用目录、虚拟环境、模型、缓存和本地配置都在 Git 忽略目录中。
- 配置器不会覆盖已有 `config.toml`。
- 配置器拒绝在仓库源码存在未提交改动时运行，避免把未知修改混入受信任环境。
- 依赖安装仍会访问 PyPI、模型站点和第三方服务；企业或高安全环境应先检查依赖锁、软件物料清单与网络策略。
- NarratoAI、VideoLingo 的部分功能会调用外部 API 或上传媒体。启用前核对隐私、内容、费用和商业授权条款。

## 硬件提示

- MoneyPrinterTurbo 的常规素材、Edge TTS 和 FFmpeg 路线通常不要求独立显卡；具体 API 与编码速度取决于环境。
- NarratoAI 的基础流程可以使用 CPU，但本地视觉、语音和克隆模型可能明显增加内存、磁盘与显存需求。
- VideoLingo 的 WhisperX、PyTorch、Demucs 和本地配音路线较重；NVIDIA GPU 能改善部分本地任务，但具体兼容性以锁定提交的官方安装器输出为准。
