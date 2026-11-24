"""插件系统与注册表测试。"""

import json
import tempfile
import unittest
from pathlib import Path

from compaq.plugins import (
    PluginError,
    check_range,
    load_plugin,
    validate_manifest,
)


def write_plugin(root: Path, name: str, manifest: dict, main_py: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    (d / manifest["entry"]).write_text(main_py, encoding="utf-8")
    return d


def good_manifest(**over) -> dict:
    m = {
        "name": "test-plugin",
        "version": "1.0.0",
        "author": "tester",
        "license": "MIT",
        "entry": "main.py",
        "compatible_with": ">=0.1.0 <1.0.0",
        "pricing": {"type": "free"},
    }
    m.update(over)
    return m


class TestRanges(unittest.TestCase):
    def test_range(self):
        self.assertTrue(check_range("0.1.0", ">=0.1.0 <1.0.0"))
        self.assertFalse(check_range("1.0.0", ">=0.1.0 <1.0.0"))
        self.assertTrue(check_range("2.3.4", "==2.3.4"))
        self.assertFalse(check_range("2.3.5", "==2.3.4"))

    def test_bad_range(self):
        with self.assertRaises(PluginError):
            check_range("1.0.0", "???")


class TestManifest(unittest.TestCase):
    def test_valid(self):
        validate_manifest(good_manifest())

    def test_missing_field(self):
        m = good_manifest()
        del m["entry"]
        with self.assertRaises(PluginError):
            validate_manifest(m)

    def test_bad_license(self):
        with self.assertRaises(PluginError):
            validate_manifest(good_manifest(license="GPL-3.0"))

    def test_bad_name(self):
        with self.assertRaises(PluginError):
            validate_manifest(good_manifest(name="Bad Name!"))

    def test_bad_pricing(self):
        with self.assertRaises(PluginError):
            validate_manifest(good_manifest(pricing={"type": "subscription"}))


class TestLoad(unittest.TestCase):
    def test_load_and_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = write_plugin(
                root,
                "hooked",
                good_manifest(name="hooked"),
                "calls = []\n"
                "def on_boot(ctx):\n"
                "    ctx.log('boot')\n"
                "    ctx.state['booted'] = True\n",
            )
            plugin = load_plugin(d, "0.1.0")
            from compaq.plugins import PluginContext, call_hook

            ctx = PluginContext(instance_name="x", instance_dir=root)
            call_hook(plugin, "on_boot", ctx)
            self.assertEqual(ctx.logs, ["boot"])
            self.assertTrue(ctx.state["booted"])

    def test_incompatible_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_plugin(
                Path(tmp),
                "future",
                good_manifest(name="future", compatible_with=">=9.0.0 <10.0.0"),
                "x = 1\n",
            )
            with self.assertRaises(PluginError):
                load_plugin(d, "0.1.0")

    def test_missing_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = write_plugin(Path(tmp), "broken", good_manifest(name="broken"), "x=1\n")
            (d / "main.py").unlink()
            with self.assertRaises(PluginError):
                load_plugin(d, "0.1.0")


class TestShippedExamples(unittest.TestCase):
    def test_examples_validate(self):
        examples = Path("examples/plugins")
        if not examples.is_dir():
            self.skipTest("examples 不存在")
        found = 0
        for manifest_path in sorted(examples.glob("*/plugin.json")):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            validate_manifest(data, source=str(manifest_path))
            self.assertTrue((manifest_path.parent / data["entry"]).is_file())
            found += 1
        self.assertGreaterEqual(found, 1)

    def test_registry_index_valid(self):
        index = Path("registry/index.json")
        if not index.is_file():
            self.skipTest("registry 不存在")
        data = json.loads(index.read_text(encoding="utf-8"))
        for entry in data.get("plugins", []):
            validate_manifest(entry, source="registry/index.json")


if __name__ == "__main__":
    unittest.main()
