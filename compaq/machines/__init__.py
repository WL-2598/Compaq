from compaq.machines import base, chip8  # noqa: F401  （注册机器）
from compaq.machines.base import MACHINES, Machine, create, pack_bits, unpack_bits

__all__ = ["MACHINES", "Machine", "create", "pack_bits", "unpack_bits"]
