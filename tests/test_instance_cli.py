"""实例管理、备份与 CLI 集成测试。"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from compaq.backup import create_backup, list_backups, restore_backup
from compaq.cli import main
from compaq.config import ConfigError, InstanceManager


class TestInstances(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.m = InstanceManager(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_list_load(self):
        self.m.ensure_home()
        self.m.create("alpha", rom="logo")
        self.m.create("beta")
        self.assertEqual(self.m.list(), ["alpha", "beta"])
        cfg = self.m.load("alpha")
        self.assertEqual(cfg.rom, "logo")

    def test_duplicate(self):
        self.m.ensure_home()
        self.m.create("dup")
        with self.assertRaises(ConfigError):
            self.m.create("dup")

    def test_bad_name(self):
        self.m.ensure_home()
        with self.assertRaises(ConfigError):
            self.m.create("Bad Name")

    def test_resolve_rom_builtin_and_file(self):
        from compaq.demo_roms import get_rom

        self.m.ensure_home()
        self.m.create("r1", rom="bounce")
        self.assertEqual(self.m.resolve_rom(self.m.load("r1")), get_rom("bounce"))
        # 写入用户 ROM
        self.m.create("r2", rom="game.ch8")
        roms = self.m.dir_for("r2") / "roms"
        (roms / "game.ch8").write_bytes(b"\x12\x00")
        self.assertEqual(self.m.resolve_rom(self.m.load("r2")), b"\x12\x00")
        # 不存在的 ROM
        missing = self.m.load("r2")
        missing.rom = "missing.ch8"
        with self.assertRaises(ConfigError):
            self.m.resolve_rom(missing)

    def test_state_roundtrip(self):
        self.m.ensure_home()
        self.m.create("s1")
        self.m.write_state("s1", {"status": "running"}, "status.json")
        self.assertEqual(self.m.read_state("s1", "status.json")["status"], "running")

    def test_backup_restore_roundtrip(self):
        self.m.ensure_home()
        self.m.create("b1", rom="logo")
        archive = create_backup(self.m, "b1")  # 先备份完好配置
        self.assertTrue(archive.is_file())
        self.assertEqual(len(list_backups(self.m, "b1")), 1)
        # 再破坏配置
        cfg_path = self.m.dir_for("b1") / "instance.json"
        cfg_path.write_text('{"name": "b1", "machine": "broken"}', encoding="utf-8")
        with self.assertRaises(ConfigError):
            self.m.load("b1")
        restore_backup(self.m, "b1", archive)
        cfg = self.m.load("b1")  # 恢复后可正常加载
        self.assertEqual(cfg.machine, "chip8")
        self.assertEqual(cfg.rom, "logo")

    def test_restore_wrong_instance_rejected(self):
        self.m.ensure_home()
        self.m.create("a1")
        self.m.create("b1")
        archive = create_backup(self.m, "a1")
        with self.assertRaises(ConfigError):
            restore_backup(self.m, "b1", archive)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = str(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *argv) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            return main(["--home", self.home, *argv])

    def test_demo_runs(self):
        rc = self._run("demo", "--frames", "60", "--no-color")
        self.assertEqual(rc, 0)
        self.assertTrue((Path(self.home) / "instances" / "demo" / "state" / "framebuffer.json").is_file())

    def test_create_list_backup(self):
        self.assertEqual(self._run("create", "cli1"), 0)
        self.assertEqual(self._run("list"), 0)
        self.assertEqual(self._run("backup", "cli1"), 0)
        self.assertEqual(self._run("backups", "cli1"), 0)
        self.assertEqual(self._run("restore", "cli1"), 0)

    def test_run_instance(self):
        self.assertEqual(self._run("create", "run1", "--rom", "bounce"), 0)
        self.assertEqual(self._run("run", "run1", "--frames", "30", "--quiet"), 0)

    def test_missing_instance_fails(self):
        self.assertEqual(self._run("run", "nope"), 1)

    def test_delete(self):
        self.assertEqual(self._run("create", "del1"), 0)
        self.assertEqual(self._run("delete", "del1", "-y"), 0)
        self.assertEqual(self._run("list"), 0)

    def test_registry_validate(self):
        self.assertEqual(self._run("registry", "validate"), 0)

    def test_doctor(self):
        self.assertEqual(self._run("doctor"), 0)

    def test_version(self):
        self.assertEqual(self._run("version"), 0)


class TestDashboardApi(unittest.TestCase):
    """轻量测试：直接调用 handler 逻辑（不起 HTTP 服务）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.m = InstanceManager(self.home)
        self.m.ensure_home()
        self.m.create("web1")
        self.m.write_state(
            "web1",
            {"width": 64, "height": 32, "pixels": "A" * 344, "frames": 1, "machine": "chip8"},
            "framebuffer.json",
        )
        self.m.write_state("web1", {"status": "running", "frames": 1}, "status.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_healthz_and_instances(self):
        from compaq.dashboard import DashboardHandler

        class FakeHandler(DashboardHandler):
            def __init__(self):
                self.responses = []

            def send_response(self, code):
                self.responses.append(("code", code))

            def send_header(self, k, v):
                pass

            def end_headers(self):
                pass

            @property
            def wfile(self):
                class W:
                    def __init__(self, owner):
                        self.owner = owner

                    def write(self, b):
                        self.owner.body = b

                return W(self)

        h = FakeHandler()
        h.manager = self.m
        h.path = "/healthz"
        h.do_GET()
        self.assertEqual(h.responses[0][1], 200)
        self.assertIn(b"ok", h.body)

        h2 = FakeHandler()
        h2.manager = self.m
        h2.path = "/api/instances"
        h2.do_GET()
        payload = json.loads(h2.body)
        self.assertEqual(payload["instances"][0]["name"], "web1")

        h3 = FakeHandler()
        h3.manager = self.m
        h3.path = "/api/instances/web1/fb"
        h3.do_GET()
        self.assertEqual(json.loads(h3.body)["frames"], 1)


if __name__ == "__main__":
    unittest.main()
