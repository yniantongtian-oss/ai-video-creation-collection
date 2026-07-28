# 本地使用说明

本仓库本身不包含模型权重，也不强制绑定某个生成框架。仓库内的目录校验和项目脚手架只依赖 Python 标准库。

## 1. 获取仓库

```bash
git clone https://github.com/yniantongtian-oss/ai-video-creation-collection.git
cd ai-video-creation-collection
```

建议使用 Python 3.10 或更高版本。

## 2. 检查资源目录

```bash
python scripts/validate_catalog.py
```

预期输出类似：

```text
Catalog OK: 10 projects, 10 unique repositories.
```

## 3. 创建视频项目

```bash
python scripts/scaffold_project.py \
  --name "城市夜景宣传片" \
  --duration 20 \
  --shot-length 4 \
  --aspect-ratio 9:16 \
  --fps 24 \
  --mode mixed
```

可用参数：

| 参数 | 说明 |
|---|---|
| `--name` | 项目名称，必填 |
| `--output` | 输出父目录，默认 `projects` |
| `--duration` | 总时长（秒），默认 15 |
| `--shot-length` | 计划单镜头时长（秒），默认 5 |
| `--aspect-ratio` | 画面比例，如 `16:9`、`9:16` |
| `--fps` | 目标帧率，默认 24 |
| `--mode` | `t2v`、`i2v`、`v2v`、`continuation` 或 `mixed` |
| `--model` | 可选的候选模型名称 |
| `--force` | 删除并重建同名项目目录，谨慎使用 |

生成目录包含：

- `brief.md`：需求、技术环境、验收标准和风险。
- `shots.csv`：按计划镜头时长自动拆分的镜头表。
- `prompts.md`：全局锚点、负向约束和镜头提示词模板。
- `manifest.json`：项目规格和可复现字段。

## 4. 安装 Agent Skill

Skill 目录：

```text
skills/ai-video-creation
```

在支持目录式 Agent Skills 的工具中，选择该目录进行安装。不同工具的安装方式可能不同，应使用该工具当前的官方说明。

Skill 加载后可以使用类似请求：

```text
为一条 30 秒、9:16 的产品宣传片建立 AI 视频制作方案。
我有 6 张产品图，使用本地 ComfyUI，显存 16GB。
请先做镜头表、模型候选、最小验证方案和提示词包，不要假设已经生成视频。
```

## 5. 接入 ComfyUI

本仓库不写死 ComfyUI、模型和自定义节点的版本。建议流程：

1. 从 ComfyUI 官方仓库或官方发行方式安装。
2. 先启动一个干净环境。
3. 选择目标模型的官方说明或经过核验的工作流。
4. 只安装该工作流需要的最小自定义节点集。
5. 使用 2–5 秒样片验证模型、VAE、文本编码器、节点和显存。
6. 保存通过验证的 workflow JSON，并把版本与节点信息写入 `manifest.json`。

## 6. 接入 Diffusers

需要 Python 自动化、批处理或服务化时：

1. 查看 Diffusers 当前官方文档是否支持目标模型。
2. 为每个项目建立独立虚拟环境。
3. 按目标 pipeline 的官方示例安装依赖。
4. 固定可复现的版本后保存依赖清单。
5. 不把 API Key、访问令牌或私有模型地址提交到 Git。

## 7. 推荐目录

实际生成项目可使用：

```text
my-video-project/
├── assets/
│   ├── audio/
│   ├── images/
│   └── video/
├── outputs/
│   ├── previews/
│   └── final/
├── workflows/
├── brief.md
├── manifest.json
├── prompts.md
└── shots.csv
```

大型模型、缓存和输出视频不应直接提交到本仓库。可使用 Git LFS、对象存储或本地项目目录，并记录来源与哈希。

## 8. 安全与授权

- 不提交密钥、Cookie、访问令牌或带签名的下载地址。
- 不使用未经授权的人脸、声音、音乐、商标或私有素材。
- 对第三方模型、权重、节点和输出分别检查许可证。
- 对社区工作流和自定义节点进行代码审查后再运行。
