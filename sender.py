#!/usr/bin/env python3
"""Beam room live sender: cuts a live MPEG-TS input into 1 s fragments and publishes each one as a Beam room message (`beam room channel publish --stdin`).

Input: a file (played once in real time, or looped) or a live source such as the MPEG-TS that OBS sends to a local UDP port.
The video needs a keyframe every second (OBS: keyframe interval 1 s; ffmpeg: -g 25 -keyint_min 25 for 25 fps), because each fragment is cut at a keyframe.

  python3 sender.py --room ROOM_ID --channel CHANNEL_ID --source 'udp://127.0.0.1:9000?fifo_size=5000000&overrun_nonfatal=1' --out ./out \
      --parallel 12 --max-age 8 --seconds 3600 [--status-file status.txt]
  python3 sender.py --room ROOM_ID --channel CHANNEL_ID --source clip.mp4 --out ./out --loop --seconds 600

Needs: the Beam CLI signed in, with this machine as a room member holding the `publish` grant on the channel, and ffmpeg.
Each message is `FRAG|<index>|<time the fragment was complete>|<session>` + newline + the MPEG-TS bytes (a message may carry up to 1 MiB).
Messages are live-only: members that are not listening when a fragment is sent never receive it."""
import argparse
import json
import os
import re
import subprocess
import threading
import time


def jl(path, rec, lock=threading.Lock()):
    with lock, open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def send(a):
    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        os.remove(os.path.join(a.out, f))
    log = os.path.join(a.out, "send.jsonl")
    live = a.source.startswith(("udp://", "rtmp://", "srt://", "tcp://"))       # a live input (OBS) is already real-time: no -re
    cmd = [a.ffmpeg, "-hide_banner", "-loglevel", "error"] + (["-stream_loop", "-1"] if a.loop and not live else []) + ([] if live else ["-re"]) + ["-i", a.source] + (["-t", str(a.seconds)] if a.seconds else []) + ["-c", "copy", "-f", "segment", "-segment_time", "1", "-segment_format", "mpegts",
           "-reset_timestamps", "0", os.path.join(a.out, "f_%05d.ts")]
    jl(log, {"ev": "start", "t": time.time()})
    p = subprocess.Popen(cmd)
    session = int(time.time())          # lets a viewer tell this run's fragments from an older run's (indices restart at 0)
    sem = threading.Semaphore(a.parallel)
    done, threads = set(), []

    status = {"ok": 0, "bad": 0, "dropped": 0, "delay": []}

    def write_status():     # the OBS side panel reads this file (text source from file)
        if not a.status_file:
            return
        d = status["delay"][-10:]
        try:
            open(a.status_file, "w").write(f"sending fragments\n\nlast publish\n{d[-1]:.1f} s\n" if d else "starting\n\nlast publish\n--\n")
        except OSError:
            pass

    def pub(i, path, t_ready):
        with sem:
            if a.max_age and time.time() - t_ready > a.max_age:      # too late to be worth sending: drop it instead of growing a backlog
                status["dropped"] += 1
                jl(log, {"ev": "drop", "i": i, "age": time.time() - t_ready})
                return
            body = f"FRAG|{i}|{t_ready:.3f}|{session}\n".encode() + open(path, "rb").read()
            t0 = time.time()
            r = subprocess.run(["beam", "room", "channel", "publish", a.room, a.channel, "--stdin", "--content-type", "video/mp2t"], input=body, capture_output=True)
            status["ok" if r.returncode == 0 else "bad"] += 1
            status["delay"].append(time.time() - t_ready)
            write_status()
            jl(log, {"ev": "pub", "i": i, "bytes": len(body), "t_ready": t_ready, "t_start": t0, "t_done": time.time(), "rc": r.returncode,
                     "err": (r.stderr or b"")[-160:].decode("utf8", "replace") if r.returncode else ""})

    while True:
        names = sorted(n for n in os.listdir(a.out) if re.fullmatch(r"f_\d+\.ts", n))
        finished = names[:-1] if p.poll() is None else names     # a fragment is complete once the next one exists
        for n in finished:
            if n in done:
                continue
            done.add(n)
            path = os.path.join(a.out, n)
            th = threading.Thread(target=pub, args=(int(n[2:7]), path, os.stat(path).st_mtime)); th.start(); threads.append(th)
        if p.poll() is not None and len(done) >= len(names):
            break
        time.sleep(0.05)
    for th in threads:
        th.join()
    jl(log, {"ev": "end", "t": time.time()})
    print("sent", len(done), "fragments", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--room", required=True); ap.add_argument("--channel", required=True); ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--source", required=True); ap.add_argument("--out", required=True); ap.add_argument("--parallel", type=int, default=12)
    ap.add_argument("--loop", action="store_true", help="repeat a file source"); ap.add_argument("--seconds", type=int, default=0, help="stop after this many seconds")
    ap.add_argument("--max-age", type=float, default=0, help="drop fragments older than this many seconds before sending (live use: 8)")
    ap.add_argument("--status-file", help="text file updated after every publish (e.g. for an OBS text source)")
    send(ap.parse_args())
