# 变更记录

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [0.1.0] - 2026-11-24

首个可运行版本——"5 分钟跑通"达成。

### Added

- **CHIP-8 虚拟机**（纯 Python，零第三方依赖）：经典 COSMAC VIP 语义、64×32 磷光屏、60Hz 定时器
- **演示 ROM**：运行时汇编生成的 `logo`（COMPAQ 开机动画）与 `bounce`（反弹小球），仓库不含二进制
- **实例管理**：`create` / `list` / `run` / `delete`，目录布局含 ROM、状态、插件、备份
- **插件系统**：`plugin.json` 清单校验（许可证白名单 + semver 兼容范围）、`on_boot` / `on_frame` / `on_stop` 钩子、示例插件 `frame-counter`
- **备份/恢复**：tar.gz 快照，含路径穿越与实例归属校验
- **Web 仪表盘**（纯 http.server）：实例列表、实时帧缓冲、`/healthz` 健康检查
- **CLI**：`demo`（5 分钟上手）、`doctor`（环境自检）、`registry validate`（注册表 CI 校验）
- **部署**：`deploy/` Dockerfile + compose（健康检查、每日备份滚动保留 7 份）
- **CI**：unittest × Python 3.9/3.12、演示冒烟、注册表校验、sdist/wheel 构建与安装验证
- 治理文件（本仓库先前已并入 main）：CONTRIBUTING（DCO）、CODE_OF_CONDUCT、SECURITY、GOVERNANCE、社区宪章、路线图

### Notes

- 运行时依赖：无（许可证审计见 `docs/third-party-licenses.md`）
- 托管服务上线前须完成 `docs/legal/hosted-service-checklist.md`

## [Unreleased]

### Added

- （空——下一版本从这里累积）
