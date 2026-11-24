# 插件注册表（registry/）

社区插件通过 PR 提交到本目录，合并后即视为官方索引收录。

## 提交流程

1. 在你的插件仓库根目录提供 `plugin.json`（规范见 `schemas/plugin.schema.json`）；
2. 发 PR，把自己的插件元数据追加进 `index.json`；
3. CI 校验格式与许可证（JSON Schema + 许可证白名单）；
4. 维护者人工审查安全性后合并。

## plugin.json 示例

```json
{
  "name": "example-plugin",
  "version": "1.0.0",
  "author": "your-github-id",
  "license": "MIT",
  "entry": "main.py",
  "compatible_with": ">=1.0.0 <2.0.0",
  "pricing": { "type": "free" }
}
```

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| name | ✅ | 全局唯一，小写字母/数字/连字符 |
| version | ✅ | 语义化版本 |
| author | ✅ | GitHub 用户名 |
| license | ✅ | 白名单：MIT / Apache-2.0 / BSD-2-Clause / BSD-3-Clause / ISC |
| entry | ✅ | 入口文件 |
| compatible_with | ✅ | 宿主版本范围（semver range） |
| pricing.type | ✅ | `free` 或 `paid`（paid 第 12 周后才开放） |
| repository | ⬜ | 插件源码仓库 URL |
| description | ⬜ | 一句话说明 |

## 审核标准

- **许可证**：不在白名单的一律拒绝；
- **安全性**：入口代码人工审查（网络访问、文件写入、子进程）；
- **兼容性**：`compatible_with` 必须与声明的 API 版本匹配；
- **命名**：不得使用与宿主品牌冲突的名称（见 `docs/naming.md`）。

## 付费插件与分成（第 12 周之后开放）

- 抽成比例：**15%**（公开承诺，结算周期随财务报告季度公开）；
- 开放前本文件会先更新并公示 2 周；
- 资金流经渠道确定后公布（Open Collective / 平台托管）。
