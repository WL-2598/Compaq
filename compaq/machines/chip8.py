"""纯 Python 实现的 CHIP-8 虚拟机（1970 年代 COSMAC VIP）。

零第三方依赖，面向老旧硬件：内存 4KB、64x32 单色屏、16 个 8 位寄存器。
指令集为经典（非 Super-CHIP）实现，兼容性取舍见 docs/architecture.md。
"""

from __future__ import annotations

import random
from typing import List, Optional

from compaq.machines.base import Machine, pack_bits, register

# 标准 0-F 十六进制字体（每字 5 字节），加载到 0x50
FONT = bytes(
    [
        0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
        0x20, 0x60, 0x20, 0x20, 0x70,  # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
        0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
        0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
        0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
        0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
        0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
    ]
)
FONT_BASE = 0x50
PROGRAM_BASE = 0x200


class Chip8Error(RuntimeError):
    pass


@register
class Chip8(Machine):
    id = "chip8"
    label = "CHIP-8 (1975 COSMAC VIP)"

    WIDTH = 64
    HEIGHT = 32

    def __init__(self, rom: bytes, seed: Optional[int] = None, cycles_per_frame: int = 20):
        super().__init__(rom)
        if len(rom) > 4096 - PROGRAM_BASE:
            raise Chip8Error(f"ROM 过大: {len(rom)} 字节（上限 {4096 - PROGRAM_BASE}）")
        self.mem = bytearray(4096)
        self.mem[FONT_BASE : FONT_BASE + len(FONT)] = FONT
        self.mem[PROGRAM_BASE : PROGRAM_BASE + len(rom)] = rom
        self.v: List[int] = [0] * 16
        self.i = 0
        self.pc = PROGRAM_BASE
        self.stack: List[int] = []
        self.delay = 0
        self.sound = 0
        self.pixels = [0] * (self.WIDTH * self.HEIGHT)
        self.keys = [False] * 16
        self.waiting_key: Optional[int] = None  # FX0A 时等待的寄存器
        self.halted = False
        self.cycles_per_frame = cycles_per_frame
        self._rng = random.Random(seed)
        self.instructions = 0

    # ---- 时钟 ----
    def step(self) -> None:
        if self.halted:
            return
        if self.waiting_key is not None:
            for k, down in enumerate(self.keys):
                if down:
                    self.v[self.waiting_key] = k
                    self.waiting_key = None
                    break
            return
        op = (self.mem[self.pc] << 8) | self.mem[self.pc + 1]
        self.pc = (self.pc + 2) & 0xFFF
        self.instructions += 1
        self._execute(op)

    def tick(self) -> None:
        if self.delay > 0:
            self.delay -= 1
        if self.sound > 0:
            self.sound -= 1

    # ---- 解码执行 ----
    def _execute(self, op: int) -> None:
        x = (op >> 8) & 0xF
        y = (op >> 4) & 0xF
        n = op & 0xF
        nn = op & 0xFF
        nnn = op & 0xFFF

        top = op >> 12
        if op == 0x00E0:  # CLS
            self.pixels = [0] * (self.WIDTH * self.HEIGHT)
        elif op == 0x00EE:  # RET
            if not self.stack:
                self.halted = True
                return
            self.pc = self.stack.pop()
        elif top == 0x0:
            return  # 其他 0NNN：忽略（现代机器不用）
        elif top == 0x1:  # JP NNN
            self.pc = nnn
        elif top == 0x2:  # CALL NNN
            self.stack.append(self.pc)
            self.pc = nnn
        elif top == 0x3:  # SE Vx, NN
            if self.v[x] == nn:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0x4:  # SNE Vx, NN
            if self.v[x] != nn:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0x5 and n == 0:  # SE Vx, Vy
            if self.v[x] == self.v[y]:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0x6:  # LD Vx, NN
            self.v[x] = nn
        elif top == 0x7:  # ADD Vx, NN（不更新 VF）
            self.v[x] = (self.v[x] + nn) & 0xFF
        elif top == 0x8:
            self._alu(x, y, n)
        elif top == 0x9 and n == 0:  # SNE Vx, Vy
            if self.v[x] != self.v[y]:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0xA:  # LD I, NNN
            self.i = nnn
        elif top == 0xB:  # JP V0, NNN（经典语义）
            self.pc = (nnn + self.v[0]) & 0xFFF
        elif top == 0xC:  # RND Vx, NN
            self.v[x] = self._rng.randrange(256) & nn
        elif top == 0xD:  # DRW Vx, Vy, N
            self._draw(x, y, n)
        elif top == 0xE and nn == 0x9E:  # SKP Vx
            if self.keys[self.v[x] & 0xF]:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0xE and nn == 0xA1:  # SKNP Vx
            if not self.keys[self.v[x] & 0xF]:
                self.pc = (self.pc + 2) & 0xFFF
        elif top == 0xF:
            self._fx(x, nn)
        else:  # pragma: no cover - 不可达
            raise Chip8Error(f"非法指令 {op:#06x} @ {self.pc - 2:#05x}")

    def _alu(self, x: int, y: int, n: int) -> None:
        if n == 0x0:
            self.v[x] = self.v[y]
        elif n == 0x1:
            self.v[x] |= self.v[y]
        elif n == 0x2:
            self.v[x] &= self.v[y]
        elif n == 0x3:
            self.v[x] ^= self.v[y]
        elif n == 0x4:  # ADD（进位 → VF）
            s = self.v[x] + self.v[y]
            self.v[x] = s & 0xFF
            self.v[0xF] = 1 if s > 0xFF else 0
        elif n == 0x5:  # SUB（借位 → VF，无借位=1）
            diff = self.v[x] - self.v[y]
            self.v[x] = diff & 0xFF
            self.v[0xF] = 1 if diff >= 0 else 0
        elif n == 0x6:  # SHR（经典：Vx >>= 1）
            self.v[0xF] = self.v[x] & 1
            self.v[x] >>= 1
        elif n == 0x7:  # SUBN
            diff = self.v[y] - self.v[x]
            self.v[x] = diff & 0xFF
            self.v[0xF] = 1 if diff >= 0 else 0
        elif n == 0xE:  # SHL
            self.v[0xF] = (self.v[x] >> 7) & 1
            self.v[x] = (self.v[x] << 1) & 0xFF
        else:
            raise Chip8Error(f"非法 ALU {n:#x}")

    def _draw(self, x: int, y: int, n: int) -> None:
        vx = self.v[x] % self.WIDTH
        vy = self.v[y] % self.HEIGHT
        self.v[0xF] = 0
        row_base = self.i
        for row in range(n):
            sprite = self.mem[(row_base + row) & 0xFFF]
            py = (vy + row) % self.HEIGHT
            for bit in range(8):
                if sprite & (0x80 >> bit):
                    px = (vx + bit) % self.WIDTH
                    idx = py * self.WIDTH + px
                    if self.pixels[idx]:
                        self.v[0xF] = 1
                    self.pixels[idx] ^= 1

    def _fx(self, x: int, nn: int) -> None:
        if nn == 0x07:  # LD Vx, DT
            self.v[x] = self.delay
        elif nn == 0x0A:  # LD Vx, [key]
            self.waiting_key = x
        elif nn == 0x15:  # LD DT, Vx
            self.delay = self.v[x]
        elif nn == 0x18:  # LD ST, Vx
            self.sound = self.v[x]
        elif nn == 0x1E:  # ADD I, Vx
            self.i = (self.i + self.v[x]) & 0xFFF
        elif nn == 0x29:  # LD F, Vx（字体地址）
            self.i = FONT_BASE + (self.v[x] & 0xF) * 5
        elif nn == 0x33:  # LD B, Vx（BCD）
            val = self.v[x]
            self.mem[self.i & 0xFFF] = val // 100
            self.mem[(self.i + 1) & 0xFFF] = (val // 10) % 10
            self.mem[(self.i + 2) & 0xFFF] = val % 10
        elif nn == 0x55:  # LD [I], Vx（经典：I 前进）
            for r in range(x + 1):
                self.mem[(self.i + r) & 0xFFF] = self.v[r]
            self.i = (self.i + x + 1) & 0xFFF
        elif nn == 0x65:  # LD Vx, [I]
            for r in range(x + 1):
                self.v[r] = self.mem[(self.i + r) & 0xFFF]
            self.i = (self.i + x + 1) & 0xFFF
        else:
            raise Chip8Error(f"非法 FX {nn:#04x}")

    # ---- 输出 ----
    def framebuffer(self) -> bytes:
        return pack_bits(self.pixels, self.WIDTH)

    def is_halted(self) -> bool:
        return self.halted

    def lit_ratio(self) -> float:
        return sum(self.pixels) / len(self.pixels)
