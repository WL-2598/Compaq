# Compaq（康柏）

**一句话定位**：康柏是一个复古计算环境项目——一键跑起复古机器（v0.1 内置 CHIP-8），用插件扩展能力，旧机器和容器都能跑。

> ⚠️ **命名声明（待办）**：项目正在进行商标检索（见 [docs/naming.md](docs/naming.md)）。正式改名后，本处将固定为：
>
> > 本项目与 Compaq 或 HP 无关联，名称仅为致敬早期计算机文化。

![演示](docs/assets/demo.png) <!-- TODO: 替换为 30 秒 GIF 截图 -->

## 快速开始（5 分钟）

只需 Python 3.9+，**零第三方依赖**：

```bash
git clone https://github.com/WL-2598/Compaq.git
cd Compaq
python -m compaq demo          # 开机动画 + 终端画面
```

想装成命令行工具：

```bash
pip install .                  # 或 pipx install .
compaq demo --watch --frames 300
```

跑通后继续：

```bash
compaq dashboard               # Web 仪表盘 → http://127.0.0.1:8642
compaq create mygame --rom bounce
compaq run mygame --watch      # 实时动画
compaq backup mygame           # 实例备份/恢复
```

## 核心功能

1. **一键复古计算环境**——`compaq demo` 一条命令跑起 CHIP-8 虚拟机（4KB 内存、64×32 磷光屏），为旧硬件设计的纯 Python 实现。
2. **实例管理**——每个环境独立目录（配置 / ROM / 状态 / 备份），`create` / `run` / `list` / `delete` 全生命周期。
3. **插件系统**——`plugin.json` 清单 + `on_boot` / `on_frame` / `on_stop` 钩子，社区以 PR 提交到 [registry/](registry/)（见[示例插件](examples/plugins/frame-counter/)）。
4. **备份与恢复**——`compaq backup` 生成 tar.gz 快照，`compaq restore` 一键回滚（含路径穿越防护）。
5. **Web 仪表盘**——纯标准库 HTTP 服务：实例列表、实时画面、`/healthz` 健康检查（托管版监控的探针）。

## 文档

| 文档 | 说明 |
|---|---|
| [快速开始](docs/quickstart.md) | 从克隆到跑通 |
| [路线图](docs/roadmap.md) | 季度计划与阶段 Gate |
| [架构说明](docs/architecture.md) | 组件、取舍、扩展点 |
| [贡献指南](CONTRIBUTING.md) | 开发流程、DCO、PR 规范 |
| [社区宪章](docs/charter.md) | 社区版承诺与决策原则 |
| [安全策略](SECURITY.md) | 漏洞私下上报渠道 |

## 部署（托管版雏形）

```bash
cd deploy && docker compose up -d   # 仪表盘 + 每日备份 + 健康检查
```

见 [deploy/README.md](deploy/README.md)。**对公众提供托管服务前须完成[法律清单](docs/legal/hosted-service-checklist.md)（须律师确认）。**

## 赞助

欢迎通过仓库顶部的 **Sponsor** 按钮赞助（三档：¥15 / ¥50 / ¥500）。资金用途每季度公开，见 [财务报告模板](docs/finance/TEMPLATE.md)。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交代码需要 DCO sign-off（`git commit -s`）。

## 许可证

[MIT](LICENSE)

## 致敬

项目名称致敬早期计算机文化中的 Compaq；本项目与 Compaq / HP 公司无关联。
