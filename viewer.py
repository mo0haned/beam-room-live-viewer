#!/usr/bin/env python3
"""Viewer page for the video-over-messages test (run on a member PC; stdlib only).

Listens on the room's video message channel (`beam --json room channel listen`), keeps each 1 s MPEG-TS fragment (payload `FRAG|<i>|<t_ready>\\n` + bytes)
and serves them to your browser as a growing HLS playlist. The video reaches this page only through Beam; HTTP is used just between this process and your
browser on localhost.

  python3 viewer.py --room ROOM_ID [--channel CHANNEL_ID] [--port 8820]"""
import argparse
import base64
import json
import os
import re
import statistics
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HLS_JS = "https://cdnjs.cloudflare.com/ajax/libs/hls.js/1.5.8/hls.min.js"
PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Beam video over messages</title>
<style>
:root{color-scheme:light dark;--b:#8884;--mut:#888}
body{margin:0;font:14px system-ui,sans-serif;background:Canvas;color:CanvasText}
header{padding:10px 16px;border-bottom:1px solid var(--b);display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
h1{font-size:16px;margin:0}.mut{color:var(--mut)}
main{display:grid;grid-template-columns:minmax(0,3fr) minmax(260px,2fr);gap:16px;padding:16px}
@media(max-width:800px){main{grid-template-columns:1fr}}
video{width:100%;background:#000;aspect-ratio:16/9;border-radius:6px}
.k{display:flex;gap:24px;margin:10px 0;flex-wrap:wrap}.k div{min-width:90px}.k b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%}th,td{text-align:right;padding:3px 8px;border-bottom:1px solid var(--b);font-variant-numeric:tabular-nums}th:first-child,td:first-child{text-align:left}
</style>
<header><h1>Video over Beam room messages</h1><span id=st class=mut>waiting for the first fragment…</span><span class=mut>480p · 1 s fragments · one Beam message each</span></header>
<main>
<section><video id=v controls muted autoplay playsinline></video>
 <div class=k><div><span class=mut>received</span><b id=n>0</b></div><div><span class=mut>missing</span><b id=miss>0</b></div><div><span class=mut>delay p50</span><b id=p50>-</b></div><div><span class=mut>delay last</span><b id=last>-</b></div><div><span class=mut>delay max</span><b id=max>-</b></div></div>
 <p class=mut>Delay = arrival here minus the moment the fragment was complete on the streamer, in seconds (<span id=sy></span>). Playback starts after 4 fragments are buffered.</p></section>
<section><table><thead><tr><th>fragment<th>complete<th>arrived<th>delay s<th>KiB</tr></thead><tbody id=rows></tbody></table></section>
</main>
<script src="__HLS__"></script>
<script>
const $=id=>document.getElementById(id);let started=false;const f=t=>new Date(t*1000).toLocaleTimeString([], {hour12:false})+'.'+String(Math.floor((t%1)*10));
async function tick(){try{const s=await (await fetch('/stats')).json();
 $('n').textContent=s.n;$('miss').textContent=s.missing;$('p50').textContent=s.p50==null?'-':s.p50.toFixed(1);$('last').textContent=s.last==null?'-':s.last.toFixed(1);$('max').textContent=s.max==null?'-':s.max.toFixed(1);
 $('sy').textContent=s.synced?'clock offset corrected':'assumes both clocks are set by NTP, so treat it as approximate';$('st').textContent=s.n?('receiving · '+s.n+' fragments'+(s.ended?' · stream ended':'')):'waiting for the first fragment…';
 $('rows').innerHTML=s.rows.slice(-18).reverse().map(r=>`<tr><td>#${r.i}<td>${r.ready?f(r.ready):'?'}<td>${f(r.arrived)}<td>${r.delay==null?'?':r.delay.toFixed(2)}<td>${(r.bytes/1024).toFixed(0)}</tr>`).join('');
 if(s.n>=4&&!started){started=true;
  if(window.Hls&&Hls.isSupported()){const h=new Hls({liveSyncDurationCount:3,liveMaxLatencyDurationCount:8,maxBufferHole:1.5});h.loadSource('/live.m3u8');h.attachMedia($('v'));$('v').play().catch(()=>{})}
  else $('v').src='/live.m3u8'}}catch(e){}}
setInterval(tick,700);tick();
</script>
""".replace("__HLS__", HLS_JS)


class State:
    def __init__(self, a):
        self.a = a
        off = json.load(open(a.offsets)) if a.offsets and os.path.exists(a.offsets) else {}
        self.off = (off.get(a.stream_host) or {}).get("offset_s", 0.0)
        self.f = {}     # i -> {"b": bytes, "arrived": t, "ready": t_ready in this PC's clock}
        self.lock = threading.Lock()
        self.last_rx = 0.0
        self.total = 0
        self.have_offsets = bool(off.get(a.stream_host))

    def listen(self):
        while True:
            p = subprocess.Popen(["beam", "--json", "room", "channel", "listen", self.a.room, self.a.channel], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            for line in p.stdout:
                t = time.time()
                try:
                    raw = base64.b64decode(json.loads(line)["payload"])
                except (ValueError, KeyError):
                    continue
                head, _, body = raw.partition(b"\n")
                m = re.match(rb"FRAG\|(\d+)\|([\d.]+)", head)
                if m and int(m.group(1)) < 900:
                    with self.lock:
                        if int(m.group(1)) not in self.f:
                            self.total += 1
                        self.f.setdefault(int(m.group(1)), {"b": body, "arrived": t, "ready": float(m.group(2)) - self.off})
                        self.last_rx = t
                        for old in sorted(self.f)[:-150]:      # keep about 2.5 minutes of fragments in memory
                            del self.f[old]
            time.sleep(1)

    def stats(self):
        with self.lock:
            ids = sorted(self.f)
            rows = [{"i": i, "ready": self.f[i]["ready"], "arrived": self.f[i]["arrived"], "delay": self.f[i]["arrived"] - self.f[i]["ready"], "bytes": len(self.f[i]["b"])} for i in ids]
        d = [r["delay"] for r in rows]
        return {"n": self.total, "missing": (ids[-1] + 1 - ids[0] - len(ids)) if ids else 0, "synced": bool(self.have_offsets), "p50": statistics.median(d) if d else None, "last": d[-1] if d else None,
                "max": max(d) if d else None, "rows": rows, "ended": bool(ids) and time.time() - self.last_rx > 8}

    def playlist(self):
        with self.lock:
            ids = sorted(self.f)[-40:]          # sliding live window: a viewer that joins late starts near the live edge
        L = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:2", f"#EXT-X-MEDIA-SEQUENCE:{ids[0] if ids else 0}"]
        prev = None
        for i in ids:
            if prev is not None and i != prev + 1:
                L.append("#EXT-X-DISCONTINUITY")
            L += ["#EXTINF:1.000,", f"/frag/{i}.ts"]
            prev = i
        return "\n".join(L) + "\n"


def handler(S):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *x):
            pass

        def send(self, code, body, ctype="application/json"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urllib.parse.urlparse(self.path).path
            if u == "/":
                return self.send(200, PAGE, "text/html; charset=utf-8")
            if u == "/stats":
                return self.send(200, S.stats())
            if u == "/live.m3u8":
                return self.send(200, S.playlist(), "application/vnd.apple.mpegurl")
            m = re.fullmatch(r"/frag/(\d+)\.ts", u)
            if m:
                with S.lock:
                    d = S.f.get(int(m.group(1)))
                return self.send(200, d["b"], "video/mp2t") if d else self.send(404, b"", "text/plain")
            self.send(404, b"", "text/plain")

    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--room", required=True); ap.add_argument("--channel", help="channel id; if omitted the channel named --channel-name is looked up in the room"); ap.add_argument("--channel-name", default="vmsg")
    ap.add_argument("--offsets"); ap.add_argument("--stream-host", default=""); ap.add_argument("--port", type=int, default=8820); ap.add_argument("--bind", default="127.0.0.1", help="listen address (the Docker image uses 0.0.0.0)")
    a = ap.parse_args()
    if not a.channel:       # find the video channel by name, so only the room id has to be shared
        out = subprocess.run(["beam", "--json", "room", "channel", "list", a.room], capture_output=True, text=True)
        try:
            a.channel = next(c["channel_id"] for c in json.loads(out.stdout).get("channels", []) if c.get("name") == a.channel_name)
        except (ValueError, StopIteration):
            raise SystemExit(f"could not find a channel named {a.channel_name!r} in {a.room}; are you a member of the room? ({(out.stderr or out.stdout)[-200:]})")
    S = State(a)
    threading.Thread(target=S.listen, daemon=True).start()
    srv = ThreadingHTTPServer((a.bind, a.port), handler(S)); srv.daemon_threads = True
    print(f"viewer: http://127.0.0.1:{a.port}/", flush=True)
    srv.serve_forever()
