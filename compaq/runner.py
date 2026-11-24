"""实例运行器：装配 机器 + 插件 + 状态输出。"""

from __future__ import annotations

import json
import signal
import time
from pathlib import Path
from typing import Optional

from compaq import __version__
from compaq.config import InstanceConfig, InstanceManager
from compaq.machines import create as create_machine
from compaq.plugins import PluginContext, call_hook, load_instance_plugins
from compaq.render import frame_to_json_pixels


class Runner:
    def __init__(self, manager: InstanceManager, cfg: InstanceConfig):
        self.manager = manager
        self.cfg = cfg
        rom = manager.resolve_rom(cfg)
        self.vm = create_machine(
            cfg.machine, rom, cycles_per_frame=cfg.cycles_per_frame
        )
        plugins_dir = manager.dir_for(cfg.name) / "plugins"
        self.plugins = load_instance_plugins(plugins_dir, cfg.plugins, __version__)
        self.ctx = PluginContext(
            instance_name=cfg.name, instance_dir=manager.dir_for(cfg.name)
        )
        self.frames = 0
        self._stop = False

    def boot(self) -> None:
        for p in self.plugins:
            call_hook(p, "on_boot", self.ctx)
        self._write_state("running")

    def step_frame(self) -> None:
        self.vm.run_frame(self.cfg.cycles_per_frame)
        for p in self.plugins:
            call_hook(p, "on_frame", self.ctx, self.vm)
        self.frames += 1

    def write_framebuffer(self) -> None:
        payload = {
            "machine": self.cfg.machine,
            "width": getattr(self.vm, "WIDTH", 64),
            "height": getattr(self.vm, "HEIGHT", 32),
            "pixels": frame_to_json_pixels(self.vm.framebuffer()),
            "frames": self.frames,
            "updated_at": time.time(),
        }
        self.manager.write_state(self.cfg.name, payload, "framebuffer.json")

    def _write_state(self, status: str, **extra) -> None:
        payload = {
            "status": status,
            "instance": self.cfg.name,
            "machine": self.cfg.machine,
            "frames": self.frames,
            "plugins": [p.name for p in self.plugins],
            "updated_at": time.time(),
            **extra,
        }
        self.manager.write_state(self.cfg.name, payload, "status.json")

    def stop(self, status: str = "stopped") -> None:
        for p in self.plugins:
            call_hook(p, "on_stop", self.ctx)
        self._write_state(status, logs=self.ctx.logs[-20:])
        self._stop = True

    # ---- 运行模式 ----
    def run_frames(self, n: int, on_frame=None, write_state: bool = True) -> None:
        """跑 n 帧后停止；on_frame 回调可做终端渲染。"""
        self.boot()
        try:
            for _ in range(n):
                if self._stop:
                    break
                self.step_frame()
                if on_frame:
                    on_frame(self)
                if write_state and self.frames % 10 == 0:
                    self.write_framebuffer()
            if write_state:
                self.write_framebuffer()
            self.stop("stopped")
        except (KeyboardInterrupt, SystemExit):
            if write_state:
                self.write_framebuffer()
            self.stop("interrupted")
            raise

    def run_daemon(self, write_state: bool = True) -> None:
        """无限运行，周期写状态，供托管版/仪表盘使用。SIGTERM/SIGINT 优雅退出。"""
        self.boot()

        def _sig(signum, frame):
            raise KeyboardInterrupt

        prev_int = signal.signal(signal.SIGINT, _sig)
        prev_term = signal.signal(signal.SIGTERM, _sig)
        interval = 1.0 / max(1, self.cfg.hz)
        try:
            while not self._stop:
                t0 = time.monotonic()
                self.step_frame()
                if write_state and self.frames % 5 == 0:
                    self.write_framebuffer()
                elapsed = time.monotonic() - t0
                if elapsed < interval:
                    time.sleep(interval - elapsed)
        except KeyboardInterrupt:
            if write_state:
                self.write_framebuffer()
            self.stop("stopped")
        finally:
            signal.signal(signal.SIGINT, prev_int)
            signal.signal(signal.SIGTERM, prev_term)
