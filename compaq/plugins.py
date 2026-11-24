"""插件系统：plugin.json 清单 + main.py 入口 + 语义化版本兼容范围。

插件钩子（全部可选）：
    on_boot(ctx)            实例启动时调用一次
    on_frame(ctx, vm)       每帧调用一次，vm 为机器对象
    on_stop(ctx)            实例停止时调用一次

安全说明（v0.1.0）：插件是本机信任代码，与主进程同权运行。
托管版在容器级隔离（见 deploy/README.md），后续版本将增加权限声明。
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

LICENSE_WHITELIST = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?$")


class PluginError(ValueError):
    pass


@dataclass
class PluginContext:
    """传给插件钩子的上下文。"""

    instance_name: str
    instance_dir: Path
    logs: List[str] = field(default_factory=list)
    state: Dict = field(default_factory=dict)

    def log(self, msg: str) -> None:
        self.logs.append(str(msg))


def parse_version(v: str) -> tuple:
    m = VERSION_RE.match(v)
    if not m:
        raise PluginError(f"非法版本号: {v}")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4) or "")


def check_range(version: str, range_expr: str) -> bool:
    """支持空格分隔的 AND 子句：>=1.2.0 <2.0.0 / ==1.0.0。"""
    ver = parse_version(version)
    for clause in range_expr.split():
        m = re.match(r"^(>=|<=|==|!=|>|<)?\s*(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$", clause)
        if not m:
            raise PluginError(f"无法解析兼容范围子句: {clause!r}")
        op = m.group(1) or "=="
        rhs = parse_version(m.group(2))
        # 预发布版本比较：忽略预发布后缀的简化比较（足够 v0.1 使用）
        a, b = ver[:3], rhs[:3]
        ok = {
            "==": a == b,
            "!=": a != b,
            ">": a > b,
            "<": a < b,
            ">=": a >= b,
            "<=": a <= b,
        }[op]
        if not ok:
            return False
    return True


def validate_manifest(data: dict, source: str = "<manifest>") -> dict:
    """校验 plugin.json（与 registry/schemas/plugin.schema.json 同规则）。"""
    required = ["name", "version", "author", "license", "entry", "compatible_with", "pricing"]
    missing = [k for k in required if k not in data]
    if missing:
        raise PluginError(f"{source}: 缺少字段 {', '.join(missing)}")
    if not isinstance(data["name"], str) or not NAME_RE.match(data["name"]):
        raise PluginError(f"{source}: 非法 name {data['name']!r}")
    if not isinstance(data["version"], str) or not VERSION_RE.match(data["version"]):
        raise PluginError(f"{source}: 非法 version {data['version']!r}")
    if data["license"] not in LICENSE_WHITELIST:
        raise PluginError(
            f"{source}: 许可证 {data['license']!r} 不在白名单（{', '.join(sorted(LICENSE_WHITELIST))}）"
        )
    if not isinstance(data["entry"], str) or not data["entry"]:
        raise PluginError(f"{source}: entry 必须是非空字符串")
    if not isinstance(data["compatible_with"], str) or not data["compatible_with"]:
        raise PluginError(f"{source}: compatible_with 必须是非空字符串")
    pricing = data["pricing"]
    if not isinstance(pricing, dict) or pricing.get("type") not in ("free", "paid"):
        raise PluginError(f"{source}: pricing.type 必须是 free 或 paid")
    # 语法检查 compatible_with（结果不重要）
    try:
        check_range("0.0.0", data["compatible_with"])
    except PluginError as e:
        raise PluginError(f"{source}: compatible_with 无效: {e}") from e
    return data


@dataclass
class Plugin:
    manifest: dict
    path: Path
    module: object = None

    @property
    def name(self) -> str:
        return self.manifest["name"]


def load_plugin(plugin_dir: Path, host_version: str) -> Plugin:
    """加载单个插件目录（plugin.json + entry 文件）。"""
    manifest_path = Path(plugin_dir) / "plugin.json"
    if not manifest_path.is_file():
        raise PluginError(f"{plugin_dir}: 缺少 plugin.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PluginError(f"{manifest_path}: JSON 解析失败: {e}") from e
    validate_manifest(manifest, source=str(manifest_path))
    if not check_range(host_version, manifest["compatible_with"]):
        raise PluginError(
            f"{manifest_path}: 要求宿主 {manifest['compatible_with']}，当前 {host_version}"
        )
    entry = Path(plugin_dir) / manifest["entry"]
    if not entry.is_file():
        raise PluginError(f"{plugin_dir}: 入口文件不存在: {manifest['entry']}")

    spec = importlib.util.spec_from_file_location(f"compaq_plugin_{manifest['name']}", entry)
    if spec is None or spec.loader is None:
        raise PluginError(f"{entry}: 无法创建模块")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return Plugin(manifest=manifest, path=Path(plugin_dir), module=module)


def call_hook(plugin: Plugin, hook: str, *args) -> None:
    fn = getattr(plugin.module, hook, None)
    if callable(fn):
        fn(*args)


def discover(instance_plugins_dir: Path) -> List[Path]:
    if not instance_plugins_dir.is_dir():
        return []
    return sorted(
        p for p in instance_plugins_dir.iterdir() if (p / "plugin.json").is_file()
    )


def load_instance_plugins(
    instance_plugins_dir: Path, enabled: List[str], host_version: str
) -> List[Plugin]:
    loaded = []
    for path in discover(instance_plugins_dir):
        plugin = load_plugin(path, host_version)
        if not enabled or plugin.name in enabled:
            loaded.append(plugin)
    return loaded
