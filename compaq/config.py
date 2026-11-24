"""实例配置与目录布局。

布局（home 默认 ./.compaq，可用环境变量 COMPAQ_HOME 覆盖）：
  .compaq/
    instances/<name>/instance.json   配置
    instances/<name>/state/          运行状态（framebuffer.json 等）
    instances/<name>/roms/           用户 ROM
    instances/<name>/backups/        备份
    instances/<name>/plugins/        实例级插件
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

CONFIG_VERSION = 1


class ConfigError(ValueError):
    pass


@dataclass
class InstanceConfig:
    name: str
    machine: str = "chip8"
    rom: str = "bounce"          # 演示 ROM 名，或 roms/ 下的相对路径
    hz: int = 60
    cycles_per_frame: int = 20
    plugins: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    config_version: int = CONFIG_VERSION

    def validate(self) -> None:
        if not NAME_RE.match(self.name):
            raise ConfigError(
                f"非法实例名 {self.name!r}：需小写字母/数字/连字符，且以字母或数字开头"
            )
        if self.machine not in ("chip8",):
            raise ConfigError(f"未知机器 {self.machine!r}（v0.1.0 仅支持 chip8）")
        if not (1 <= self.hz <= 240):
            raise ConfigError("hz 必须在 1..240 之间")
        if not (1 <= self.cycles_per_frame <= 1000):
            raise ConfigError("cycles_per_frame 必须在 1..1000 之间")


def default_home() -> Path:
    env = os.environ.get("COMPAQ_HOME")
    if env:
        return Path(env).expanduser()
    return Path.cwd() / ".compaq"


class InstanceManager:
    def __init__(self, home: Optional[Path] = None):
        self.home = Path(home) if home else default_home()

    @property
    def instances_dir(self) -> Path:
        return self.home / "instances"

    def ensure_home(self) -> None:
        self.instances_dir.mkdir(parents=True, exist_ok=True)

    def dir_for(self, name: str) -> Path:
        if not NAME_RE.match(name):
            raise ConfigError(f"非法实例名 {name!r}")
        return self.instances_dir / name

    def exists(self, name: str) -> bool:
        return (self.dir_for(name) / "instance.json").is_file()

    def load(self, name: str) -> InstanceConfig:
        path = self.dir_for(name) / "instance.json"
        if not path.is_file():
            raise ConfigError(f"实例不存在: {name}")
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg = InstanceConfig(**data)
        cfg.validate()
        return cfg

    def save(self, cfg: InstanceConfig) -> Path:
        cfg.validate()
        d = self.dir_for(cfg.name)
        for sub in ("", "state", "roms", "backups", "plugins"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        path = d / "instance.json"
        path.write_text(
            json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    def create(self, name: str, machine: str = "chip8", rom: str = "bounce", **kw) -> InstanceConfig:
        if self.exists(name):
            raise ConfigError(f"实例已存在: {name}")
        cfg = InstanceConfig(name=name, machine=machine, rom=rom, **kw)
        self.save(cfg)
        return cfg

    def list(self) -> List[str]:
        if not self.instances_dir.is_dir():
            return []
        names = []
        for p in sorted(self.instances_dir.iterdir()):
            if (p / "instance.json").is_file():
                names.append(p.name)
        return names

    def delete(self, name: str) -> None:
        import shutil

        if not self.exists(name):
            raise ConfigError(f"实例不存在: {name}")
        shutil.rmtree(self.dir_for(name))

    def resolve_rom(self, cfg: InstanceConfig) -> bytes:
        """解析实例 ROM：演示名 → 内置生成；否则从 roms/ 读取。"""
        from compaq.demo_roms import ROMS, get_rom

        if cfg.rom in ROMS:
            return get_rom(cfg.rom)
        rom_path = self.dir_for(cfg.name) / "roms" / cfg.rom
        if not rom_path.is_file():
            raise ConfigError(
                f"找不到 ROM {cfg.rom!r}（内置: {', '.join(sorted(ROMS))}；"
                f"或放入 {rom_path}）"
            )
        return rom_path.read_bytes()

    def write_state(self, name: str, payload: dict, filename: str = "state.json") -> Path:
        state_dir = self.dir_for(name) / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / filename
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return path

    def read_state(self, name: str, filename: str = "state.json") -> Optional[dict]:
        path = self.dir_for(name) / "state" / filename
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
