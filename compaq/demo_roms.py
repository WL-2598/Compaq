"""内置演示 ROM：用一个微型汇编器在运行时生成（仓库不含二进制文件）。

提供两个 ROM：
- logo   ：闪烁的 "COMPAQ" 开机动画
- bounce ：四边反弹的小球（经典屏幕保护器风格）
"""

from __future__ import annotations

from typing import Dict, List, Union


class Asm:
    """两遍微型 CHIP-8 汇编器：支持标签、跳转 fixup 与 .db 数据。"""

    def __init__(self, base: int = 0x200):
        self.base = base
        self.items: List[tuple] = []  # ("w", word) | ("db", bytes) | ("label", name)
        self.fixups: List[tuple] = []  # (item_index, kind, label, low_bits)

    def _emit(self, item):
        self.items.append(item)
        return len(self.items) - 1

    # 数据
    def db(self, *vals: int) -> "Asm":
        self._emit(("db", bytes(vals)))
        return self

    def label(self, name: str) -> "Asm":
        self._emit(("label", name))
        return self

    def _op(self, word: int) -> "Asm":
        self._emit(("w", word))
        return self

    def _addr(self, word_hi: int, target: Union[int, str]) -> "Asm":
        """word_hi 提供高 4 位（1=JP, 2=CALL, A=LD I, B=JP V0），低 12 位来自地址/标签。"""
        if isinstance(target, str):
            idx = self._emit(("w", word_hi << 12))  # 占位，稍后回填
            self.fixups.append((idx, target))
        else:
            self._op((word_hi << 12) | (target & 0xFFF))
        return self

    # 指令
    def cls(self): return self._op(0x00E0)
    def ret(self): return self._op(0x00EE)
    def jp(self, t): return self._addr(0x1, t)
    def call(self, t): return self._addr(0x2, t)
    def se_v(self, x, nn): return self._op(0x3000 | (x << 8) | nn)
    def sne_v(self, x, nn): return self._op(0x4000 | (x << 8) | nn)
    def se_vv(self, x, y): return self._op(0x5000 | (x << 8) | (y << 4))
    def ld_v(self, x, nn): return self._op(0x6000 | (x << 8) | nn)
    def add_v(self, x, nn): return self._op(0x7000 | (x << 8) | nn)
    def ld_vv(self, x, y): return self._op(0x8000 | (x << 8) | (y << 4))
    def or_vv(self, x, y): return self._op(0x8001 | (x << 8) | (y << 4))
    def and_vv(self, x, y): return self._op(0x8002 | (x << 8) | (y << 4))
    def xor_vv(self, x, y): return self._op(0x8003 | (x << 8) | (y << 4))
    def add_vv(self, x, y): return self._op(0x8004 | (x << 8) | (y << 4))
    def sub_vv(self, x, y): return self._op(0x8005 | (x << 8) | (y << 4))
    def shr_v(self, x): return self._op(0x8006 | (x << 8))
    def subn_vv(self, x, y): return self._op(0x8007 | (x << 8) | (y << 4))
    def shl_v(self, x): return self._op(0x800E | (x << 8))
    def sne_vv(self, x, y): return self._op(0x9000 | (x << 8) | (y << 4))
    def ld_i(self, t): return self._addr(0xA, t)
    def jp_v0(self, t): return self._addr(0xB, t)
    def rnd_v(self, x, nn): return self._op(0xC000 | (x << 8) | nn)
    def drw(self, x, y, n): return self._op(0xD000 | (x << 8) | (y << 4) | n)
    def skp(self, x): return self._op(0xE09E | (x << 8))
    def sknp(self, x): return self._op(0xE0A1 | (x << 8))
    def ld_dt_v(self, x): return self._op(0xF007 | (x << 8))
    def wait_key(self, x): return self._op(0xF00A | (x << 8))
    def ld_v_dt(self, x): return self._op(0xF015 | (x << 8))
    def ld_v_st(self, x): return self._op(0xF018 | (x << 8))
    def add_i_v(self, x): return self._op(0xF01E | (x << 8))
    def ld_f_v(self, x): return self._op(0xF029 | (x << 8))
    def ld_b_v(self, x): return self._op(0xF033 | (x << 8))
    def st_regs(self, x): return self._op(0xF055 | (x << 8))
    def ld_regs(self, x): return self._op(0xF065 | (x << 8))

    def assemble(self) -> bytes:
        # 第一遍：算标签地址
        labels: Dict[str, int] = {}
        addr = self.base
        for item in self.items:
            if item[0] == "label":
                labels[item[1]] = addr
            elif item[0] == "w":
                addr += 2
            elif item[0] == "db":
                addr += len(item[1])
        # 第二遍：回填
        out = bytearray()
        for idx, item in enumerate(self.items):
            if item[0] == "label":
                continue
            if item[0] == "w":
                word = item[1]
                for fix_idx, fix_label in self.fixups:
                    if fix_idx == idx:
                        if fix_label not in labels:
                            raise ValueError(f"未定义标签: {fix_label}")
                        word = (word & 0xF000) | (labels[fix_label] & 0xFFF)
                out += bytes([(word >> 8) & 0xFF, word & 0xFF])
            else:
                out += item[1]
        return bytes(out)


def build_logo_rom() -> bytes:
    """'COMPAQ' 闪烁开机动画。"""
    a = Asm()
    # 自定义字形（O/M/P/Q），各 5 字节，位于代码之后
    # 布局：先放代码，数据标签在尾部
    a.ld_v(0, 18)   # V0 = 列
    a.ld_v(1, 13)   # V1 = 行
    a.call("draw_word")
    # 点亮 30 tick
    a.ld_v(6, 30)
    a.ld_v_dt(6)
    a.label("wait_on")
    a.ld_dt_v(6)
    a.se_v(6, 0)
    a.jp("wait_on")
    a.cls()
    # 熄灭 10 tick
    a.ld_v(6, 10)
    a.ld_v_dt(6)
    a.label("wait_off")
    a.ld_dt_v(6)
    a.se_v(6, 0)
    a.jp("wait_off")
    a.jp("draw_word")  # 回到子程序入口重画（V0/V1 已被子程序重置）
    # ---- draw_word 子程序 ----
    a.label("draw_word")
    a.ld_v(0, 18)
    a.ld_v(1, 13)
    # C：字体第 12 个字（0x50 + 12*5 = 0x8A）
    a.ld_i(0x8A)
    a.drw(0, 1, 5)
    a.add_v(0, 5)
    # O
    a.ld_i("spr_o")
    a.drw(0, 1, 5)
    a.add_v(0, 5)
    # M
    a.ld_i("spr_m")
    a.drw(0, 1, 5)
    a.add_v(0, 5)
    # P
    a.ld_i("spr_p")
    a.drw(0, 1, 5)
    a.add_v(0, 5)
    # A：字体第 10 个（0x50 + 10*5 = 0x82）
    a.ld_i(0x82)
    a.drw(0, 1, 5)
    a.add_v(0, 5)
    # Q
    a.ld_i("spr_q")
    a.drw(0, 1, 5)
    a.ret()
    # ---- 字形数据 ----
    a.label("spr_o")
    a.db(0xF0, 0x90, 0x90, 0x90, 0xF0)
    a.label("spr_m")
    a.db(0x90, 0xF0, 0x90, 0x90, 0x90)
    a.label("spr_p")
    a.db(0xF0, 0x90, 0xF0, 0x80, 0x80)
    a.label("spr_q")
    a.db(0xF0, 0x90, 0x90, 0xF0, 0x10)
    return a.assemble()


def build_bounce_rom() -> bytes:
    """四边反弹的小球。"""
    a = Asm()
    a.ld_v(2, 20)   # V2 = x
    a.ld_v(3, 8)    # V3 = y
    a.ld_v(4, 1)    # V4 = dx
    a.ld_v(5, 1)    # V5 = dy
    a.label("loop")
    a.cls()
    a.ld_i("ball")
    a.drw(2, 3, 4)
    a.add_vv(2, 4)  # x += dx
    a.add_vv(3, 5)  # y += dy
    # x 边界：0 与 60（球宽 4）
    a.se_v(2, 0)
    a.jp("chk_xmax")
    a.ld_v(4, 1)
    a.label("chk_xmax")
    a.se_v(2, 60)
    a.jp("chk_ymin")
    a.ld_v(4, 0xFF)
    a.label("chk_ymin")
    a.se_v(3, 0)
    a.jp("chk_ymax")
    a.ld_v(5, 1)
    a.label("chk_ymax")
    a.se_v(3, 28)
    a.jp("loop")
    a.ld_v(5, 0xFF)
    a.jp("loop")
    a.label("ball")
    a.db(0x60, 0xF0, 0xF0, 0x60)
    return a.assemble()


ROMS = {
    "logo": build_logo_rom,
    "bounce": build_bounce_rom,
}


def get_rom(name: str) -> bytes:
    if name not in ROMS:
        raise ValueError(f"未知演示 ROM {name!r}，可用: {', '.join(sorted(ROMS))}")
    return ROMS[name]()
