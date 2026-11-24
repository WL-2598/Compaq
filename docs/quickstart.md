# 快速开始

**验收标准**：一个从未接触项目的人，只看本页即可在 5 分钟内跑通——这是唯一有效的测试。

## 前置条件

- Python **3.9+**（`python3 --version` 查看）
- 无需 Docker、无需任何第三方包（零依赖设计，老机器友好）

## 5 分钟路径

```bash
# 1. 获取代码
git clone https://github.com/WL-2598/Compaq.git
cd Compaq

# 2. 跑通：开机动画（COMPAQ 字样闪烁）
python -m compaq demo
```

看到终端里的绿色像素画面和"✔ 跑通了"即成功。数据写入 `./.compaq/`（已 gitignore）。

## 第二步：动画预览与仪表盘

```bash
python -m compaq run demo --watch --frames 300    # 终端实时动画（小球）
python -m compaq dashboard                        # 浏览器打开 http://127.0.0.1:8642
```

仪表盘会显示实例列表和实时画面；`/healthz` 返回 `{"status":"ok"}`。

## 第三步：创建你自己的实例

```bash
python -m compaq create mygame --rom bounce       # 或 --rom <你自己的ROM文件名>
python -m compaq list
python -m compaq run mygame --watch
python -m compaq backup mygame                    # 备份
python -m compaq restore mygame                   # 恢复最新备份
```

自己的 ROM 放到 `.compaq/instances/mygame/roms/` 下，然后 `--rom <文件名>`。

## 可选：安装为命令行工具

```bash
pip install .          # 安装后可直接用 `compaq` 命令
# 或: pipx install .
compaq version
```

## 遇到问题？

```bash
python -m compaq doctor    # 环境自检（Python、目录、虚拟机、注册表）
```

仍失败 → 用 [Bug 模板](https://github.com/WL-2598/Compaq/issues/new?template=bug_report.yml) 开 Issue，附上 `doctor` 输出。

## 下一步

- 了解设计 → [架构说明](architecture.md)
- 写插件 → [registry/ 规范](https://github.com/WL-2598/Compaq/blob/main/registry/README.md)
- 参与贡献 → [贡献指南](contributing.md)
