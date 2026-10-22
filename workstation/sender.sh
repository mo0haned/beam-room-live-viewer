#!/bin/bash
# Starts the OBS-to-Beam sender on the workstation (user streamer): reads OBS's MPEG-TS from udp://127.0.0.1:9000, publishes 1 s fragments as room messages.
#   obs_box_sender.sh start | stop | status       (set ROOM and CHANNEL in the environment)
ROOM=${ROOM:?set ROOM to the room id}
CHANNEL=${CHANNEL:?set CHANNEL to the video channel id}
export PATH=$HOME/.local/bin:$PATH
OUT=$HOME/out
case "${1:-status}" in
  start) pgrep -f '[b]eammsg.py send' >/dev/null && { echo "already running"; exit 0; }
         mkdir -p $OUT; rm -f $OUT/*
         (nohup python3 $HOME/livetest/beammsg.py send --room $ROOM --channel $CHANNEL --ffmpeg /usr/bin/ffmpeg --source 'udp://127.0.0.1:9000?fifo_size=5000000&overrun_nonfatal=1' \
            --out $OUT --parallel 12 --max-age 8 --seconds ${SECONDS_TO_RUN:-3600} --status-file $HOME/overlay/status.txt > $HOME/send.out 2>&1 &)
         sleep 3; pgrep -f '[b]eammsg.py send' | wc -l | sed 's/^/sender processes: /' ;;
  stop)  pkill -f '[b]eammsg.py send'; pkill -f '[f]fmpeg .*udp://127.0.0.1:9000'; sleep 1; echo stopped ;;
  status) pgrep -f '[b]eammsg.py send' | wc -l | sed 's/^/sender processes: /'
          python3 - <<'PY'
import json, os
f = os.path.expanduser("~/out/send.jsonl")
r = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
p = [x for x in r if x["ev"] == "pub"]; d = [x for x in r if x["ev"] == "drop"]
print("published", len(p), "ok", sum(1 for x in p if x["rc"] == 0), "dropped", len(d), "| ready->done s (last 8):", [round(x["t_done"] - x["t_ready"], 1) for x in p[-8:]])
PY
          ;;
esac
