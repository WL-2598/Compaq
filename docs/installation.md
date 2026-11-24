# 安装

## 方式一：直接运行（推荐，零依赖）

```bash
git clone https://github.com/WL-2598/Compaq.git
cd Compaq
python3 -m compaq demo
```

- 需要 **Python 3.9+**，无需 pip 安装任何东西
- 适合旧机器、受限环境、只想快速体验

## 方式二：安装为命令行工具

```bash
cd Compaq
pip install .        # 或 pipx install .（隔离环境，推荐）
compaq version
```

卸载：`pip uninstall compaq`。

## 方式三：Docker（托管/服务器）

```bash
cd deploy
docker compose up -d
# 仪表盘 → http://localhost:8642
```

镜像基于 `python:3.12-slim`，非 root 运行，内置健康检查与每日备份服务。详见 [deploy/README.md](https://github.com/WL-2598/Compaq/blob/main/deploy/README.md)。

## 系统要求

| 项 | 最低 | 说明 |
|---|---|---|
| Python | 3.9 | 仅标准库 |
| 内存 | ~30MB | 实例 + 虚拟机 4KB 内存 |
| 磁盘 | <5MB | 代码 + 实例数据 |
| 网络 | 不需要 | 除克隆仓库外完全离线 |

## 验证安装

```bash
python3 -m compaq doctor
```

输出四项 ✔ 即环境就绪。
