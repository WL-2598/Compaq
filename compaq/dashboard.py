"""Web 仪表盘：纯标准库 HTTP 服务，查看实例与画面（托管版 MVP 的雏形）。

路由：
  GET /                         单页 UI
  GET /healthz                  健康检查（监控/告警用）
  GET /api/instances            实例列表 + 状态
  GET /api/instances/<n>/fb     帧缓冲（base64 位图）
"""

from __future__ import annotations

import base64
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from compaq import __version__
from compaq.config import InstanceManager

HTML_PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>康柏 Compaq 仪表盘</title>
<style>
  :root { --bg:#0d1117; --panel:#161b22; --fg:#c9d1d9; --green:#3fb950; --dim:#8b949e; }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
         background:var(--bg); color:var(--fg); }
  header { padding:14px 20px; border-bottom:1px solid #30363d; display:flex;
           align-items:center; gap:14px; }
  h1 { font-size:16px; margin:0; letter-spacing:2px; color:var(--green); }
  .badge { font-size:11px; background:var(--panel); border:1px solid #30363d;
           border-radius:10px; padding:1px 8px; color:var(--dim); }
  main { display:flex; gap:16px; padding:16px 20px; flex-wrap:wrap; }
  #list { min-width:240px; background:var(--panel); border:1px solid #30363d;
          border-radius:8px; padding:12px; }
  #list h2 { font-size:12px; color:var(--dim); margin:0 0 8px; text-transform:uppercase; }
  .inst { padding:8px 10px; border-radius:6px; cursor:pointer; margin-bottom:6px;
          border:1px solid transparent; }
  .inst:hover { background:#21262d; }
  .inst.active { border-color:var(--green); background:#21262d; }
  .inst .st { float:right; font-size:11px; color:var(--dim); }
  .inst .st.running { color:var(--green); }
  #screen { background:#000; border:1px solid #30363d; border-radius:8px;
            padding:14px; text-align:center; }
  canvas { image-rendering: pixelated; background:#001800;
           border:1px solid #1f3a24; border-radius:4px; max-width:100%; }
  #meta { color:var(--dim); font-size:12px; margin-top:8px; }
  #empty { color:var(--dim); padding:30px; }
  .hint { color:var(--dim); font-size:12px; padding:0 20px 20px; }
  code { color:var(--green); }
</style>
</head>
<body>
<header>
  <h1>COMPAQ 康柏</h1>
  <span class="badge">v__VERSION__</span>
  <span class="badge" id="health">…</span>
</header>
<main>
  <aside id="list"><h2>实例</h2><div id="items">加载中…</div></aside>
  <section id="screen">
    <canvas id="cv" width="640" height="320"></canvas>
    <div id="meta">选择左侧实例</div>
  </section>
</main>
<div class="hint">启动实例：<code>python -m compaq run &lt;名&gt; --daemon</code>
 · 健康检查：<code>/healthz</code> · 画面每 300ms 自动刷新</div>
<script>
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
let current = null;
async function jget(url) { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.json(); }
async function refreshList() {
  try {
    const data = await jget('/api/instances');
    document.getElementById('health').textContent = 'ok · ' + data.instances.length + ' 实例';
    const box = document.getElementById('items');
    if (!data.instances.length) { box.innerHTML = '<div id="empty">暂无实例<br><br>运行：<br><code>python -m compaq demo</code></div>'; return; }
    box.innerHTML = '';
    for (const it of data.instances) {
      const el = document.createElement('div');
      el.className = 'inst' + (current === it.name ? ' active' : '');
      el.innerHTML = '<span class="st ' + (it.status||'') + '">' + (it.status||'—') + '</span><b>' + it.name + '</b><br><small>' + it.machine + ' · ' + it.rom + '</small>';
      el.onclick = () => { current = it.name; refreshList(); refreshFb(); };
      box.appendChild(el);
    }
  } catch (e) { document.getElementById('health').textContent = 'offline'; }
}
async function refreshFb() {
  if (!current) return;
  try {
    const fb = await jget('/api/instances/' + current + '/fb');
    const raw = atob(fb.pixels);
    const W = fb.width, H = fb.height;
    cv.width = W * 10; cv.height = H * 10;
    ctx.fillStyle = '#001800'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = '#3fb950';
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const byte = raw.charCodeAt(y * Math.ceil(W / 8) + (x >> 3));
      if (byte & (0x80 >> (x & 7))) ctx.fillRect(x * 10, y * 10, 10, 10);
    }
    document.getElementById('meta').textContent =
      current + ' · ' + fb.machine + ' · frame ' + fb.frames;
  } catch (e) { document.getElementById('meta').textContent = current + ' · 未运行'; }
}
refreshList(); refreshFb();
setInterval(refreshList, 2000);
setInterval(refreshFb, 300);
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    manager: InstanceManager = None  # type: ignore[assignment]

    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            html = HTML_PAGE.replace("__VERSION__", __version__)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/healthz":
            self._json(200, {"status": "ok", "version": __version__})
        elif path == "/api/instances":
            items = []
            for name in self.manager.list():
                cfg = self.manager.load(name)
                st = self.manager.read_state(name, "status.json") or {}
                items.append(
                    {
                        "name": name,
                        "machine": cfg.machine,
                        "rom": cfg.rom,
                        "status": st.get("status", "stopped"),
                        "frames": st.get("frames", 0),
                    }
                )
            self._json(200, {"instances": items})
        else:
            m = re.match(r"^/api/instances/([a-z0-9-]+)/fb$", path)
            if m:
                name = m.group(1)
                fb = self.manager.read_state(name, "framebuffer.json")
                if not fb:
                    self._json(404, {"error": "no framebuffer（实例尚未运行）"})
                    return
                self._json(200, fb)
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")


def run_dashboard(host: str = "127.0.0.1", port: int = 8642, home: Optional[Path] = None) -> None:
    manager = InstanceManager(home)
    handler = type("BoundHandler", (DashboardHandler,), {"manager": manager})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"康柏仪表盘: http://{host}:{port}  (Ctrl-C 退出)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()
