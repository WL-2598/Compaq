"""compaq 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from compaq import __version__
from compaq.backup import create_backup, list_backups, restore_backup
from compaq.config import ConfigError, InstanceManager, default_home
from compaq.plugins import PluginError, discover, validate_manifest
from compaq.render import render_ascii, should_color


def _manager(args) -> InstanceManager:
    home = Path(args.home) if getattr(args, "home", None) else None
    return InstanceManager(home)


def _print_frame(vm, color: bool) -> None:
    width = getattr(vm, "WIDTH", 64)
    height = getattr(vm, "HEIGHT", 32)
    rows = []
    pixels = getattr(vm, "pixels", None)
    if pixels is None:
        from compaq.machines.base import unpack_bits

        rows = unpack_bits(vm.framebuffer(), width, height)
        flat = [p for row in rows for p in row]
    else:
        flat = pixels
    print(render_ascii(flat, width, height, color=color))


# ---- 子命令 ----
def cmd_create(args) -> int:
    m = _manager(args)
    m.ensure_home()
    cfg = m.create(args.name, machine=args.machine, rom=args.rom)
    print(f"已创建实例 {cfg.name}（machine={cfg.machine}, rom={cfg.rom}）")
    print(f"位置: {m.dir_for(cfg.name)}")
    print(f"下一步: python -m compaq run {cfg.name} --frames 120")
    return 0


def cmd_list(args) -> int:
    m = _manager(args)
    names = m.list()
    if not names:
        print("暂无实例。创建: python -m compaq create <名字>")
        return 0
    for name in names:
        cfg = m.load(name)
        st = m.read_state(name, "status.json") or {}
        status = st.get("status", "stopped")
        print(f"  {name:<20} {cfg.machine:<8} rom={cfg.rom:<10} status={status}")
    return 0


def cmd_delete(args) -> int:
    m = _manager(args)
    if not args.yes:
        answer = input(f"确认删除实例 {args.name}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消")
            return 1
    m.delete(args.name)
    print(f"已删除 {args.name}")
    return 0


def cmd_run(args) -> int:
    from compaq.runner import Runner

    m = _manager(args)
    cfg = m.load(args.name)
    runner = Runner(m, cfg)
    color = should_color(False if args.no_color else (True if args.color else None))

    if args.daemon:
        print(f"运行 {args.name}（daemon 模式，Ctrl-C 退出）…")
        runner.run_daemon()
        print("已停止")
        return 0

    def on_frame(r):
        if args.watch and not args.quiet:
            print("\033[2J\033[H", end="")
            _print_frame(r.vm, color)
            print(
                f"\n{args.name} · frame {r.frames} · plugins: "
                f"{', '.join(p.name for p in r.plugins) or '无'}"
            )

    runner.run_frames(args.frames, on_frame=on_frame if args.watch else None)
    if not args.quiet and not args.watch:
        print(f"\n{args.name} 运行 {runner.frames} 帧完成（状态已写入 state/）\n")
        _print_frame(runner.vm, color)
    return 0


def cmd_demo(args) -> int:
    """5 分钟上手：创建 demo 实例并跑一段开机动画。"""
    from compaq.runner import Runner

    m = _manager(args)
    m.ensure_home()
    if not m.exists("demo"):
        m.create("demo", rom=args.rom)
        print("已创建演示实例 demo")
    cfg = m.load("demo")
    if args.rom != cfg.rom:  # 允许 demo --rom 切换
        cfg.rom = args.rom
        m.save(cfg)
    runner = Runner(m, cfg)
    color = should_color(False if args.no_color else (True if args.color else None))
    print(f"启动 CHIP-8 · ROM={cfg.rom} · {args.frames} 帧 …\n")
    runner.run_frames(args.frames)
    _print_frame(runner.vm, color)
    print(
        "\n✔ 跑通了！接下来：\n"
        f"  python -m compaq run demo --watch --frames 300   # 动画预览\n"
        f"  python -m compaq dashboard                        # Web 仪表盘\n"
        f"  python -m compaq backup demo                      # 备份实例\n"
        f"  详见 docs/quickstart.md"
    )
    return 0


def cmd_dashboard(args) -> int:
    from compaq.dashboard import run_dashboard

    run_dashboard(host=args.host, port=args.port, home=Path(args.home) if args.home else None)
    return 0


def cmd_backup(args) -> int:
    m = _manager(args)
    path = create_backup(m, args.name)
    print(f"备份完成: {path} ({path.stat().st_size} 字节)")
    return 0


def cmd_backups(args) -> int:
    m = _manager(args)
    items = list_backups(m, args.name)
    if not items:
        print("无备份")
        return 0
    for p in items:
        print(f"  {p.name}  ({p.stat().st_size} 字节)")
    return 0


def cmd_restore(args) -> int:
    m = _manager(args)
    archive = Path(args.file) if args.file else None
    path = restore_backup(m, args.name, archive)
    print(f"已恢复到 {path}")
    return 0


def cmd_plugins(args) -> int:
    m = _manager(args)
    cfg = m.load(args.name)
    plugins = discover(m.dir_for(args.name) / "plugins")
    if not plugins:
        print(f"实例 {args.name} 没有插件。")
        print("创建: mkdir -p <实例目录>/plugins/<插件名> 并添加 plugin.json + main.py")
        print("示例: examples/plugins/")
        return 0
    for p in plugins:
        manifest = json.loads((p / "plugin.json").read_text(encoding="utf-8"))
        enabled = not cfg.plugins or manifest["name"] in cfg.plugins
        mark = "●" if enabled else "○"
        print(
            f"  {mark} {manifest['name']:<20} v{manifest['version']:<8} "
            f"{manifest['license']:<12} {manifest.get('description', '')}"
        )
    return 0


def cmd_registry(args) -> int:
    """registry validate：校验注册表索引与示例插件清单。"""
    if args.action != "validate":
        print(f"未知 action: {args.action}", file=sys.stderr)
        return 2
    root = Path(args.path)
    errors: List[str] = []

    schema = root / "schemas" / "plugin.schema.json"
    if not schema.is_file():
        errors.append(f"缺少 {schema}")
    index = root / "index.json"
    if not index.is_file():
        errors.append(f"缺少 {index}")
    else:
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
            plugins = data.get("plugins")
            if not isinstance(plugins, list):
                errors.append("index.json: 'plugins' 必须是数组")
            else:
                for i, entry in enumerate(plugins):
                    try:
                        validate_manifest(entry, source=f"index.json[{i}]")
                    except PluginError as e:
                        errors.append(str(e))
        except json.JSONDecodeError as e:
            errors.append(f"index.json: JSON 解析失败: {e}")

    # 校验 examples 下所有插件清单
    examples = Path("examples") / "plugins"
    if examples.is_dir():
        for manifest_path in sorted(examples.glob("*/plugin.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                validate_manifest(data, source=str(manifest_path))
                entry = manifest_path.parent / data["entry"]
                if not entry.is_file():
                    errors.append(f"{manifest_path}: 入口文件不存在: {data['entry']}")
            except (json.JSONDecodeError, PluginError) as e:
                errors.append(str(e))

    if errors:
        print(f"注册表校验失败（{len(errors)} 项）:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print("✔ 注册表校验通过")
    return 0


def cmd_doctor(args) -> int:
    """环境自检：Python、目录、CHIP-8 自检、注册表。"""
    ok = True

    def check(label, fn):
        nonlocal ok
        try:
            detail = fn()
            print(f"  ✔ {label}" + (f" — {detail}" if detail else ""))
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  ✗ {label} — {e}")

    print(f"康柏自检 v{__version__}")
    check("Python >= 3.9", lambda: sys.version.split()[0] if sys.version_info >= (3, 9) else (_ for _ in ()).throw(RuntimeError("需要 3.9+")))

    def _home():
        m = InstanceManager(Path(args.home) if args.home else None)
        m.ensure_home()
        return str(m.home)
    check("实例目录可写", _home)

    def _chip8():
        from compaq.demo_roms import get_rom
        from compaq.machines import create

        vm = create("chip8", get_rom("logo"))
        for _ in range(120):
            vm.run_frame(30)
        ratio = vm.lit_ratio()
        if ratio <= 0:
            raise RuntimeError("画面全黑")
        return f"logo ROM 亮屏比例 {ratio:.1%}"
    check("CHIP-8 自检", _chip8)

    def _registry():
        from io import StringIO
        from contextlib import redirect_stdout

        ns = argparse.Namespace(action="validate", path="registry")
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cmd_registry(ns)
        if rc != 0:
            raise RuntimeError(buf.getvalue().strip())
        return "registry OK"
    check("插件注册表", _registry)

    print("自检" + ("通过 ✔" if ok else "未通过 ✗"))
    return 0 if ok else 1


def cmd_version(_args) -> int:
    print(f"compaq {__version__}")
    return 0


# ---- 参数解析 ----
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compaq",
        description="康柏 Compaq — 复古计算环境（CHIP-8 起步，插件扩展）",
    )
    p.add_argument("--home", help="实例根目录（默认 ./.compaq 或 $COMPAQ_HOME）")
    sub = p.add_subparsers(dest="command")

    sp = sub.add_parser("create", help="创建实例")
    sp.add_argument("name")
    sp.add_argument("--machine", default="chip8", help="机器类型（默认 chip8）")
    sp.add_argument("--rom", default="bounce", help="演示 ROM 名或 roms/ 下文件名")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("list", help="列出实例")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("delete", help="删除实例")
    sp.add_argument("name")
    sp.add_argument("-y", "--yes", action="store_true", help="跳过确认")
    sp.set_defaults(func=cmd_delete)

    sp = sub.add_parser("run", help="运行实例")
    sp.add_argument("name")
    sp.add_argument("--frames", type=int, default=180, help="运行帧数（默认 180）")
    sp.add_argument("--daemon", action="store_true", help="后台常驻（供托管版/仪表盘）")
    sp.add_argument("--watch", action="store_true", help="终端实时预览")
    sp.add_argument("--quiet", action="store_true", help="不打印画面")
    sp.add_argument("--color", action="store_true", help="强制彩色输出")
    sp.add_argument("--no-color", action="store_true", help="禁用彩色输出")
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("demo", help="5 分钟演示：跑通开机动画")
    sp.add_argument("--frames", type=int, default=180)
    sp.add_argument("--rom", default="logo", choices=["logo", "bounce"])
    sp.add_argument("--color", action="store_true")
    sp.add_argument("--no-color", action="store_true")
    sp.set_defaults(func=cmd_demo)

    sp = sub.add_parser("dashboard", help="启动 Web 仪表盘")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8642)
    sp.set_defaults(func=cmd_dashboard)

    sp = sub.add_parser("backup", help="备份实例")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_backup)

    sp = sub.add_parser("backups", help="列出备份")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_backups)

    sp = sub.add_parser("restore", help="恢复实例（默认最新备份）")
    sp.add_argument("name")
    sp.add_argument("file", nargs="?", help="备份文件路径")
    sp.set_defaults(func=cmd_restore)

    sp = sub.add_parser("plugins", help="查看实例插件")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_plugins)

    sp = sub.add_parser("registry", help="插件注册表操作")
    sp.add_argument("action", choices=["validate"])
    sp.add_argument("--path", default="registry")
    sp.set_defaults(func=cmd_registry)

    sp = sub.add_parser("doctor", help="环境自检")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("version", help="显示版本")
    sp.set_defaults(func=cmd_version)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except (ConfigError, PluginError, ValueError, FileNotFoundError, OSError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
