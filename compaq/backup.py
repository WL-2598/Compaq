"""实例备份与恢复：tar.gz 快照（排除 backups/ 自身）。"""

from __future__ import annotations

import tarfile
import time
from pathlib import Path
from typing import List, Optional

from compaq.config import ConfigError, InstanceManager


def create_backup(manager: InstanceManager, name: str) -> Path:
    if not manager.exists(name):
        raise ConfigError(f"实例不存在: {name}")
    src = manager.dir_for(name)
    backups = src / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = backups / f"{name}-{stamp}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        for item in sorted(src.iterdir()):
            if item.name == "backups":
                continue
            tar.add(item, arcname=f"{name}/{item.name}")
    return out


def list_backups(manager: InstanceManager, name: str) -> List[Path]:
    backups = manager.dir_for(name) / "backups"
    if not backups.is_dir():
        return []
    return sorted(backups.glob(f"{name}-*.tar.gz"))


def restore_backup(manager: InstanceManager, name: str, archive: Optional[Path] = None) -> Path:
    """恢复备份到实例目录。archive 为空时用最新一份。"""
    if archive is None:
        candidates = list_backups(manager, name)
        if not candidates:
            raise ConfigError(f"实例 {name} 没有备份")
        archive = candidates[-1]
    archive = Path(archive)
    if not archive.is_file():
        raise ConfigError(f"备份文件不存在: {archive}")

    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        # 安全检查：只接受 <name>/... 前缀，拒绝路径穿越
        for m in members:
            if m.name.startswith("/") or ".." in Path(m.name).parts:
                raise ConfigError(f"备份包含非法路径: {m.name}")
            if not m.name.split("/")[0] == name:
                raise ConfigError(f"备份属于 {m.name.split('/')[0]!r}，与目标实例 {name!r} 不符")
        try:
            tar.extractall(manager.dir_for(name).parent, filter="data")
        except TypeError:  # Python < 3.12 无 filter 参数（已做手工路径检查）
            tar.extractall(manager.dir_for(name).parent)

    cfg_path = manager.dir_for(name) / "instance.json"
    if not cfg_path.is_file():
        raise ConfigError("恢复后缺少 instance.json，备份可能损坏")
    return manager.dir_for(name)
