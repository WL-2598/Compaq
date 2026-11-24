# 贡献指南（文档站版）

完整贡献指南见仓库根目录的 [CONTRIBUTING.md](https://github.com/WL-2598/Compaq/blob/main/CONTRIBUTING.md)，此处只列要点。

## 三件事

1. **DCO sign-off**：`git commit -s`，无 sign-off 的 PR 会被 CI 拒绝；
2. **PR 模板全部栏目**：变更说明、检查清单、AI 生成代码声明（如有）；
3. **行为准则**：见 [CODE_OF_CONDUCT.md](https://github.com/WL-2598/Compaq/blob/main/CODE_OF_CONDUCT.md)。

## 本地预览文档站

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

## 文档贡献同样欢迎

- 修正错别字、补全示例、翻译——都是有效贡献；
- 文档 PR 同样需要 sign-off；
- 新页面记得加入 `mkdocs.yml` 的 `nav`。
