# 贡献指南

感谢你对康柏（Compaq）的兴趣！v0.1.0 已发布，欢迎代码、文档、插件与内容贡献。

## 行为准则

参与本项目即表示你同意遵守 [行为准则](CODE_OF_CONDUCT.md)。

## 本地开发（零依赖）

```bash
git clone https://github.com/WL-2598/Compaq.git
cd Compaq

# 运行测试（仅标准库 unittest）
python3 -m unittest discover -s tests -v

# 冒烟
python3 -m compaq demo --frames 60 --no-color
python3 -m compaq doctor
python3 -m compaq registry validate

# 可选：装成命令行工具
pip install -e .
```

文档站预览：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-docs.txt
.venv/bin/mkdocs serve
```

## 贡献方式（DCO）

提交代码需要在 commit 中加入 sign-off，表示你有权贡献该代码，并同意以本项目许可证（MIT）发布：

```bash
git commit -s -m "fix: 修复某某问题"
```

我们使用 DCO（Developer Certificate of Origin）。未带 sign-off 的 PR 会被 CI 拒绝：

```bash
# 补救最近一次提交
git commit --amend -s --no-edit
```

如果未来需要双授权（企业版），则将 DCO 升级为 CLA，使用 cla-assistant 机器人（见 [GOVERNANCE.md](GOVERNANCE.md)）。

## 开发流程

1. Fork 仓库，从 `main` 拉出分支：`feat/...`、`fix/...`、`docs/...`、`chore/...`
2. 保持提交小而聚焦，使用约定式提交（Conventional Commits）
3. **测试必须通过**：`python3 -m unittest discover -s tests`（新行为请附测试）
4. 发起 PR，填写 PR 模板全部栏目
5. CI（DCO、test、CodeQL、docs）通过 + 至少 1 名维护者批准后合并
6. 禁止向 `main` 直接推送或强制推送

## 贡献插件（不必改核心代码）

```bash
mkdir -p my-plugin
# 编写 plugin.json + main.py（钩子: on_boot / on_frame / on_stop）
# 规范: registry/README.md   示例: examples/plugins/frame-counter/
python3 -m compaq registry validate
```

把插件目录放进某实例的 `plugins/` 即可加载；发布到注册表则提 PR 更新 `registry/index.json`。

## AI 生成代码的声明

如果你使用 AI 工具生成代码：

- 在 PR 描述中说明生成方式与用途；
- 对大段 AI 生成代码做人工审查，确保理解每一行；
- 你必须能够说明代码来源与授权，且有权按 MIT 贡献。

无法说明来源的代码不会被合并。

## PR 规范

- 已通过本地测试
- commit 已带 sign-off（`git commit -s`）
- 文档已同步更新（行为变化需更新 CHANGELOG）
- 不包含与功能无关的改动

## 发布节奏

采用语义化版本（SemVer）。每月一个 minor 版本，固定在每月第一个周二发布；变更记录见 [CHANGELOG.md](CHANGELOG.md)。打 `v*.*.*` 标签自动触发 GitHub Release。

## 提问与报告

- Bug → [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.yml)
- 功能想法 → [功能请求模板](.github/ISSUE_TEMPLATE/feature_request.yml)
- 安全问题 → 私下上报，见 [SECURITY.md](SECURITY.md)，**不要开公开 Issue**
