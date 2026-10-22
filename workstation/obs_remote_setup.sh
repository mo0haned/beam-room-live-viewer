#!/bin/bash
# Enables OBS's built-in remote control (obs-websocket) on the streaming workstation for user `streamer`: port 4455 with a random password stored in
# ~/.obs_ws_pw (mode 600, never printed). The port is also blocked for every non-loopback interface with an iptables rule, so only local scripts can use it.
set -euo pipefail
U=streamer; H=/home/$U
[ -s $H/.obs_ws_pw ] || { openssl rand -hex 12 > $H/.obs_ws_pw; chmod 600 $H/.obs_ws_pw; }
PW=$(cat $H/.obs_ws_pw)
# this OBS build (obs-websocket 5.3.x) keeps the server settings in global.ini; OBS must be closed so it does not overwrite the file on exit
pgrep -u $U -x obs >/dev/null && { echo "close OBS first"; exit 1; }
python3 - "$H/.config/obs-studio/global.ini" "$PW" <<'PY'
import sys, re
f, pw = sys.argv[1], sys.argv[2]
t = open(f).read() if __import__("os").path.exists(f) else ""
t = re.sub(r"\[OBSWebSocket\].*?(?=\n\[|\Z)", "", t, flags=re.S).rstrip() + "\n"
t += f"\n[OBSWebSocket]\nFirstLoad=false\nServerEnabled=true\nAlertsEnabled=false\nServerPort=4455\nAuthRequired=true\nServerPassword={pw}\n"
open(f, "w").write(t)
PY
chown -R $U:$U $H/.config/obs-studio $H/.obs_ws_pw
iptables -C INPUT ! -i lo -p tcp --dport 4455 -j DROP 2>/dev/null || iptables -I INPUT ! -i lo -p tcp --dport 4455 -j DROP
echo "obs-websocket configured; external access to 4455 dropped: $(iptables -S INPUT | grep -c 'dport 4455')"
