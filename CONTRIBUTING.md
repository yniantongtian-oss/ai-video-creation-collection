# 贡献指南

感谢补充 AI 视频创作相关的模型、框架、工具和 Skill。仓库目标是保持**可信、可执行、可维护**，而不是收录数量最多。

## 收录标准

优先收录：

- 模型或框架的官方仓库。
- 有明确文档、许可证和维护记录的项目。
- 能补充现有能力，而不是仅换一个包装名称的工具。
- 对本地工作流、研究、训练、批处理或 Agent Skills 有明确价值的项目。

谨慎或不收录：

- 无许可证、来源不明或只有二进制文件的仓库。
- 通过夸张宣传、虚假 Stars 或未验证性能吸引用户的项目。
- 仅提供模型下载转载，无法确认权重来源的仓库。
- 带有明文密钥、恶意安装脚本或高风险依赖的项目。
- 长期无人维护且已有可靠替代的项目。

## 修改资源目录

编辑 `catalog/projects.json`。每条项目必须包含：

```json
{
  "id": "lowercase-kebab-case",
  "name": "Project Name",
  "category": "video-model",
  "repository": "https://github.com/owner/repository",
  "official": true,
  "license": "See upstream LICENSE and model terms",
  "capabilities": ["text-to-video"],
  "when_to_use": "说明何时使用。",
  "notes": "说明限制与核验事项。"
}
```

允许的分类由 `scripts/validate_catalog.py` 中的 `ALLOWED_CATEGORIES` 定义。需要新增分类时，应同时说明理由并修改校验脚本。

## 描述规范

- 不写 Stars 数。
- 不使用“最强”“第一”“一定能跑”等无法长期验证的表述。
- 显存、速度、分辨率和时长使用环境相关描述，并提供验证方法。
- 区分官方项目、社区节点、社区量化和第三方工作流。
- 许可证不确定时写 `See upstream LICENSE and model terms`，不要猜测。
- URL 指向仓库根目录，不使用搜索结果、分支页面或下载跳转地址。

## 修改 Skill

`skills/ai-video-creation/SKILL.md` 应保持聚焦：

- 放触发条件、决策流程、执行规则和输出要求。
- 详细表格、长说明和排错内容放入 `references/`。
- 可复制模板放入 `templates/`。
- 不把当前流行项目列表全部堆进主 Skill。
- 不声称 Agent 拥有其实际没有的本地 GPU、视频生成工具或后台执行能力。

## 本地检查

提交前运行：

```bash
python scripts/validate_catalog.py
python -m py_compile scripts/*.py

# 可选：建立一个临时项目，确认脚手架正常
python scripts/scaffold_project.py \
  --name "ci-smoke-test" \
  --output /tmp/ai-video-creation-test \
  --duration 7 \
  --shot-length 3 \
  --aspect-ratio 16:9 \
  --mode mixed
```

检查生成结果后删除临时目录。

## Pull Request 说明

PR 描述至少包括：

- 修改目的。
- 新增或删除的项目。
- 官方来源和许可证核验结果。
- 运行过的检查。
- 仍然存在的不确定项或后续工作。

一个 PR 尽量只处理一个主题，避免把资源更新、Skill 重写和无关格式化混在一起。
