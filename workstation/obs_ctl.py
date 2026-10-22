#!/usr/bin/env python3
"""Tiny OBS remote-control client (obs-websocket v5, stdlib only): switch scenes while OBS stays minimized.

  obs_ctl.py scenes                list the scenes and the current one
  obs_ctl.py scene "Fullscreen"    switch to a scene by name (a unique prefix or a number from `scenes` also works)
  obs_ctl.py record-status         is the recording output running

Connects to ws://127.0.0.1:4455 with the password in ~/.obs_ws_pw (written by obs_box_ws_setup.sh; never printed)."""
import base64
import hashlib
import json
import os
import socket
import struct
import sys


def ws_connect(host, port):
    s = socket.create_connection((host, port), timeout=8)
    key = base64.b64encode(os.urandom(16)).decode()
    s.sendall((f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
               f"Sec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: obswebsocket.json\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        buf += s.recv(4096)
    if b" 101 " not in buf.split(b"\r\n")[0]:
        raise SystemExit("websocket handshake failed: " + buf.split(b"\r\n")[0].decode(errors="replace"))
    return s


def ws_send(s, text):
    data = text.encode()
    hdr = bytes([0x81])
    n = len(data)
    hdr += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n)
    mask = os.urandom(4)
    s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def ws_recv(s):
    def rd(n):
        b = b""
        while len(b) < n:
            c = s.recv(n - len(b))
            if not c:
                raise SystemExit("connection closed")
            b += c
        return b
    h = rd(2)
    n = h[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", rd(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", rd(8))[0]
    return json.loads(rd(n).decode())


def connect():
    pw = open(os.path.expanduser("~/.obs_ws_pw")).read().strip()
    s = ws_connect("127.0.0.1", 4455)
    hello = ws_recv(s)["d"]
    ident = {"rpcVersion": 1}
    if "authentication" in hello:
        a = hello["authentication"]
        secret = base64.b64encode(hashlib.sha256((pw + a["salt"]).encode()).digest()).decode()
        ident["authentication"] = base64.b64encode(hashlib.sha256((secret + a["challenge"]).encode()).digest()).decode()
    ws_send(s, json.dumps({"op": 1, "d": ident}))
    if ws_recv(s)["op"] != 2:
        raise SystemExit("OBS rejected the login")
    return s


def request(s, typ, data=None):
    ws_send(s, json.dumps({"op": 6, "d": {"requestType": typ, "requestId": "1", **({"requestData": data} if data else {})}}))
    while True:
        m = ws_recv(s)
        if m["op"] == 7:
            d = m["d"]
            if not d["requestStatus"]["result"]:
                raise SystemExit(f"{typ} failed: {d['requestStatus'].get('comment')}")
            return d.get("responseData", {})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scenes"
    s = connect()
    if cmd in ("scenes", "scene"):
        r = request(s, "GetSceneList")
        names = [x["sceneName"] for x in sorted(r["scenes"], key=lambda x: x["sceneIndex"])]
        if cmd == "scenes":
            for i, n in enumerate(names, 1):
                print(("* " if n == r["currentProgramSceneName"] else "  ") + f"{i}  {n}")
        else:
            want = sys.argv[2]
            hit = [n for n in names if n == want] or ([names[int(want) - 1]] if want.isdigit() and 0 < int(want) <= len(names) else []) or [n for n in names if n.lower().startswith(want.lower())]
            if len(hit) != 1:
                raise SystemExit(f"no unique scene for {want!r}; scenes: {names}")
            request(s, "SetCurrentProgramScene", {"sceneName": hit[0]})
            print("scene:", hit[0])
    elif cmd == "record-status":
        print(json.dumps(request(s, "GetRecordStatus")))
