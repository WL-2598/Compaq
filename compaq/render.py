"""终端渲染：ANSI 彩色（磷光绿）与纯 ASCII 回退。"""

from __future__ import annotations

import sys
from typing import Optional

ANSI_GREEN = "\033[32m"
ANSI_DIM = "\033[2m"
ANSI_RESET = "\033[0m"
ANSI_CLEAR = "\033[2J\033[H"


def render_ascii(pixels, width: int = 64, height: int = 32, color: bool = False) -> str:
    """把 0/1 像素行渲染为文本。彩色用 ██，ASCII 用 #。"""
    on, off = ("██", "  ") if color else ("##", "  ")
    lines = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        line = "".join(on if p else off for p in row)
        lines.append(line.rstrip() if not color else line)
    text = "\n".join(lines)
    if color:
        text = f"{ANSI_GREEN}{text}{ANSI_RESET}"
    return text


def should_color(explicit: Optional[bool] = None) -> bool:
    if explicit is not None:
        return explicit
    return sys.stdout.isatty()


def frame_to_json_pixels(framebuffer: bytes) -> str:
    """framebuffer 位图 → base64（供仪表盘）。"""
    import base64

    return base64.b64encode(framebuffer).decode("ascii")
