# 架构说明

## 总览

```
                ┌──────────────────────────────────────────┐
                │              compaq CLI                   │
                │  create / run / demo / backup / dashboard │
                └───────┬──────────────────────┬────────────┘
                        │                      │
              ┌─────────▼─────────┐   ┌────────▼─────────┐
              │ InstanceManager   │   │    Runner         │
              │ .compaq/instances │   │  机器+插件+状态    │
              └─────────┬─────────┘   └───┬─────────┬────┘
                        │                 │         │
              ┌─────────▼────────┐  ┌─────▼───┐ ┌───▼────────┐
              │  插件系统         │  │ Machine │ │ 状态写入     │
              │ plugin.json+钩子  │  │ chip8   │ │ state/*.json│
              └──────────────────┘  │(纯Python)│ └─────┬──────┘
                                    └─────────┘       │
                                              ┌───────▼────────┐
                                              │ Web 仪表盘      │
                                              │ /api/… + /healthz│
                                              └────────────────┘
```

## 设计取舍

1. **旧机器优先**——运行时**零第三方依赖**（纯标准库）：CHIP-8 虚拟机、HTTP 仪表盘、备份全是 stdlib 实现。代价是没有 numpy 加速、没有 FastAPI 生态；收益是 `git clone` 后一条命令跑通、许可证审计恒为零风险。
2. **状态即文件**——运行状态写 `state/*.json`（原子写：临时文件 + rename），仪表盘只读文件不走进程间通信。简单、可 grep、崩溃后状态可读。
3. **ROM 运行时生成**——演示 ROM 由内置微型汇编器生成，仓库不含二进制文件，diff 友好。
4. **插件是本机信任代码**——v0.1 与主进程同权；托管版用**容器级隔离**（每用户一容器，见 `deploy/README.md`）。后续版本增加插件权限声明。
5. **企业功能外置**——`ee/` 只放新增模块，核心永远在社区版（社区宪章）。

## CHIP-8 兼容性说明

- 经典（COSMAC VIP）语义：`FX55/FX65` 后 I 前进、`BXNN` 用 `V0`、`8XY6/8XYE` 移位 `Vx` 自身；
- 不实现 Super-CHIP / XO-CHIP 扩展（v0.1 范围外）；
- 64×32 单色、60Hz 定时器、每帧默认 20 条指令（`cycles_per_frame` 可配）。

## 扩展点

| 想做什么 | 改哪里 |
|---|---|
| 新机器（如 6502、DOS 容器） | 实现 `compaq.machines.base.Machine` 并 `@register`，在 `InstanceConfig.validate` 放开白名单 |
| 新插件钩子 | `Runner` 中 `call_hook` 调用点 + `plugins.py` 文档 |
| 托管版计费/多用户 | `deploy/` 编排层，不动核心 |
| ADR | 随版本沉淀到 `docs/adr/`（自 v0.2 起） |

## 数据流（一帧）

`Runner.step_frame` → `vm.run_frame(cycles)`（指令 + 定时器）→ 各插件 `on_frame(ctx, vm)` → 每 N 帧写 `state/framebuffer.json`（base64 位图）→ 仪表盘 300ms 轮询渲染到 canvas。
