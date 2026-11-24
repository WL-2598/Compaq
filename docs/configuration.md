# 配置参考

## 全局：环境变量与参数

| 配置 | 默认 | 说明 |
|---|---|---|
| `COMPAQ_HOME` | `./.compaq` | 实例根目录；所有子命令也接受 `--home <路径>` |
| `compaq dashboard --host` | `127.0.0.1` | 监听地址；容器内用 `0.0.0.0` |
| `compaq dashboard --port` | `8642` | 端口（0x2222，致敬） |

## 实例配置：`instance.json`

路径：`.compaq/instances/<name>/instance.json`

```json
{
  "name": "mygame",
  "machine": "chip8",
  "rom": "bounce",
  "hz": 60,
  "cycles_per_frame": 20,
  "plugins": [],
  "created_at": 1763950000.0,
  "config_version": 1
}
```

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| `name` | string | `^[a-z0-9][a-z0-9-]{0,63}$` | 实例名，即目录名 |
| `machine` | string | v0.1 仅 `chip8` | 机器类型 |
| `rom` | string | 演示名（`logo`/`bounce`）或 `roms/` 下文件名 | 启动 ROM |
| `hz` | int | 1–240 | daemon 模式帧率 |
| `cycles_per_frame` | int | 1–1000 | 每帧指令数（越大越快） |
| `plugins` | string[] | 空 = 启用全部已安装插件 | 白名单模式 |
| `config_version` | int | 1 | 配置迁移版本 |

## 目录布局

```
.compq/                        # 或 $COMPAQ_HOME
└── instances/<name>/
    ├── instance.json          # 上表配置
    ├── state/
    │   ├── status.json        # running/stopped + 插件日志尾部
    │   └── framebuffer.json   # base64 位图（仪表盘读取）
    ├── roms/                  # 用户 ROM（.ch8）
    ├── plugins/<plugin>/      # 实例级插件（plugin.json + main.py）
    └── backups/*.tar.gz       # 快照（滚动保留由备份脚本控制）
```

## 插件清单：`plugin.json`

字段与校验规则见 [registry/README.md](https://github.com/WL-2598/Compaq/blob/main/registry/README.md)；
机器可读 schema：`registry/schemas/plugin.schema.json`；校验命令：`compaq registry validate`。
