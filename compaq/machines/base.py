"""机器抽象：每种复古机器实现 Machine 接口。"""

from __future__ import annotations

from typing import Dict, Optional


class Machine:
    """一台（模拟的）复古机器。"""

    id: str = "base"
    label: str = "Base machine"

    def __init__(self, rom: bytes, **_options):
        self.rom = rom

    @property
    def width(self) -> int:  # pragma: no cover - 接口
        raise NotImplementedError

    @property
    def height(self) -> int:  # pragma: no cover - 接口
        raise NotImplementedError

    def step(self) -> None:
        """执行一条指令。"""
        raise NotImplementedError

    def tick(self) -> None:
        """推进一个 60Hz 时钟周期（定时器）。"""
        raise NotImplementedError

    def run_frame(self, cycles: int = 20) -> None:
        """运行一帧：cycles 条指令 + 一次时钟 tick。"""
        for _ in range(cycles):
            self.step()
        self.tick()

    def framebuffer(self) -> bytes:
        """返回打包的像素位图（1 bit/pixel，行优先）。"""
        raise NotImplementedError

    def is_halted(self) -> bool:
        return False


def pack_bits(pixels, width: int) -> bytes:
    """把 0/1 像素序列打包为位图字节。"""
    out = bytearray()
    acc = 0
    n = 0
    for p in pixels:
        acc = (acc << 1) | (1 if p else 0)
        n += 1
        if n == 8:
            out.append(acc)
            acc = 0
            n = 0
    if n:
        out.append(acc << (8 - n))
    return bytes(out)


def unpack_bits(data: bytes, width: int, height: int):
    """把位图字节展开为二维 0/1 列表（供渲染/测试用）。"""
    rows = []
    idx = 0
    for _ in range(height):
        row = []
        for _ in range(width):
            byte = data[idx // 8]
            bit = (byte >> (7 - (idx % 8))) & 1
            row.append(bit)
            idx += 1
        rows.append(row)
    return rows


MACHINES: Dict[str, type] = {}


def register(machine_cls):
    MACHINES[machine_cls.id] = machine_cls
    return machine_cls


def create(machine_id: str, rom: bytes, **options) -> Machine:
    if machine_id not in MACHINES:
        known = ", ".join(sorted(MACHINES)) or "(none)"
        raise ValueError(f"未知机器类型 {machine_id!r}，可用: {known}")
    return MACHINES[machine_id](rom, **options)
