"""CHIP-8 虚拟机单元测试。"""

import unittest

from compaq.demo_roms import build_bounce_rom, build_logo_rom, get_rom
from compaq.machines.base import unpack_bits
from compaq.machines.chip8 import Chip8, FONT_BASE


def tiny_rom(*words: int) -> bytes:
    out = bytearray()
    for w in words:
        out += bytes([(w >> 8) & 0xFF, w & 0xFF])
    return bytes(out)


class TestChip8Core(unittest.TestCase):
    def test_ld_and_add(self):
        # LD V0,5 / LD V1,3 / ADD V0,V1 / JP self
        rom = tiny_rom(0x6005, 0x6103, 0x8014, 0x1206)
        vm = Chip8(rom)
        for _ in range(10):
            vm.step()
        self.assertEqual(vm.v[0], 8)

    def test_cls_clears(self):
        rom = tiny_rom(0x6000, 0x6100, 0xA20A, 0xD011, 0x00E0, 0x1208)
        # 简单数据字节跟在代码后：DRW 画 1 行 sprite
        rom = rom + bytes([0x80])  # i=0x20A 指向这里? 计算: 0x200+0=.. 直接构造
        vm = Chip8(rom, seed=1)
        # 手动设置: 跑到画完
        for _ in range(20):
            vm.step()
        # CLS 已执行（或在画之前）——用 lit 比例检查最终为 0 或画过
        # 更确定的测试：先跑到 D011 前
        vm2 = Chip8(rom, seed=1)
        vm2.i = 0x20A
        vm2.v[0] = 0
        vm2.v[1] = 0
        vm2.step()  # D011? pc 不对，直接调用 draw
        vm2._draw(0, 1, 1)
        self.assertTrue(any(vm2.pixels))
        vm2._execute(0x00E0)
        self.assertFalse(any(vm2.pixels))

    def test_draw_collision_sets_vf(self):
        rom = tiny_rom(0x1200)  # JP self（不会执行 draw）
        vm = Chip8(rom, seed=1)
        vm.i = 0x300
        vm.mem[0x300] = 0xFF
        vm.v[0] = 0
        vm.v[1] = 0
        vm._draw(0, 1, 1)
        vm._draw(0, 1, 1)  # 第二次 XOR 撞上 → VF=1
        self.assertEqual(vm.v[0xF], 1)
        self.assertFalse(any(vm.pixels))

    def test_bcd_and_memory(self):
        rom = tiny_rom(0x1200)
        vm = Chip8(rom)
        vm.v[0] = 213
        vm.i = 0x400
        vm._execute(0xF033)
        self.assertEqual([vm.mem[0x400], vm.mem[0x401], vm.mem[0x402]], [2, 1, 3])

    def test_font_address(self):
        vm = Chip8(b"\x12\x00")
        vm.v[0] = 0xA
        vm._execute(0xF029)
        self.assertEqual(vm.i, FONT_BASE + 0xA * 5)

    def test_rom_too_large(self):
        with self.assertRaises(Exception):
            Chip8(b"\x00" * (4096 - 0x200 + 1))


class TestDemoRoms(unittest.TestCase):
    def test_logo_lights_pixels(self):
        vm = Chip8(build_logo_rom(), seed=1)
        for _ in range(180):
            vm.run_frame(30)
        self.assertGreater(vm.lit_ratio(), 0.005)  # 至少点亮几十个像素
        self.assertLess(vm.lit_ratio(), 0.5)

    def test_bounce_moves(self):
        vm = Chip8(build_bounce_rom(), seed=1)
        seen = set()
        for _ in range(120):
            vm.run_frame(30)
            seen.add(tuple(vm.pixels))
        self.assertGreater(len(seen), 3)  # 画面在变化
        self.assertGreater(vm.lit_ratio(), 0)

    def test_rom_sizes(self):
        for name in ("logo", "bounce"):
            self.assertLessEqual(len(get_rom(name)), 4096 - 0x200, name)

    def test_halt_on_empty_stack_ret(self):
        vm = Chip8(tiny_rom(0x00EE))
        vm.step()
        self.assertTrue(vm.is_halted())


class TestUnpack(unittest.TestCase):
    def test_pack_unpack_roundtrip(self):
        from compaq.machines.base import pack_bits

        pixels = [1, 0, 1, 0, 1, 0, 1, 0] * 8  # 64 bits
        packed = pack_bits(pixels, 64)
        self.assertEqual(len(packed), 8)
        rows = unpack_bits(packed + b"\x00" * 0, 64, 1)
        self.assertEqual(rows[0][:8], [1, 0, 1, 0, 1, 0, 1, 0])


if __name__ == "__main__":
    unittest.main()
