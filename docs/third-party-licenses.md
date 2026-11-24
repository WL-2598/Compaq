# 第三方许可证审计

- 最近扫描：2026-11-24（随 v0.1.0）
- 扫描范围：仓库根目录
- 结果：**运行时零第三方依赖**（`pyproject.toml` 中 `dependencies = []`，代码仅用 Python 标准库），无许可证风险。
  - 开发/测试：标准库 `unittest`，无额外包
  - 文档站（仅构建期）：`mkdocs` + `mkdocs-material`（MIT / CC BY-NC-SA），见 `requirements-docs.txt`
  - CI 工具：`build`（MIT），不随产品分发

## 重新扫描

```bash
# Python
pip install pip-licenses && pip-licenses --format=markdown > docs/third-party-licenses.md

# Node
npx license-checker --summary

# 通用（推荐）
pip install scancode-toolkit
scancode -l --json-pp scan.json .
```

## 引入依赖时的规则

1. 新增依赖必须在本文件登记：名称、版本、许可证；
2. **GPL / AGPL 等强传染性许可证默认禁止引入**；确需引入时记录到 `docs/license-risk.md`，说明替换或隔离（独立进程 / 子模块）方案，并经维护者投票；
3. MIT / Apache-2.0 / BSD / ISC 等宽松许可证可直接引入，注意保留版权声明。

## 风险项

无（当前零依赖）。出现 GPL/AGPL 时新建 `docs/license-risk.md` 记录。
