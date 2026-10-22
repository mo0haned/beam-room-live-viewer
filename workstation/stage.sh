#!/bin/bash
# Stage helper for the streaming workstation (run as user `streamer` inside the desktop session, or: su - streamer -c "DISPLAY=:1 ...").
#   stage.sh prepare   open OBS with the "Discord" scene so you can check the preview, Discord maximized
#   stage.sh live      start OBS recording (MPEG-TS to udp://127.0.0.1:9000), then minimize OBS and raise Discord, so only Discord's cropped centre is captured
#   stage.sh scene N   switch scene while live (1 Starting soon, 2 Discord framed, 3 Game, 4 Be right back, 5 Fullscreen, 6 Whole desktop) through OBS's local remote-control port (obs_ctl.py); a number or a name
#   stage.sh stop      stop OBS
#   stage.sh status    window state (no screenshots are taken)
# The capture is the screen region of the maximized Discord window with the left sidebars, member list and top bar cropped away (see obs_box_discord_scene.sh).
export DISPLAY=${DISPLAY:-:1}
run_obs() { ( nohup obs --profile BeamLive --collection BeamLive --scene "${SCENE:-Discord}" --disable-shutdown-check "$@" > /tmp/obs.log 2>&1 & ); }
discord_front() { wmctrl -x -r discord.discord -b add,maximized_vert,maximized_horz; wmctrl -x -a discord.discord; }
case "${1:-status}" in
  prepare) pgrep -x obs >/dev/null || run_obs; sleep 5; discord_front; echo "OBS open: check the preview, then run: stage.sh live" ;;
  live)    pgrep -x obs >/dev/null && { echo "OBS is already running; stop it first"; exit 1; }
           run_obs --startrecording; sleep 8
           xdotool search --class obs windowminimize %@ 2>/dev/null; sleep 1; discord_front; echo "recording to udp://127.0.0.1:9000; OBS minimized, Discord in front" ;;
  scene)   python3 "$HOME/livetest/obs_ctl.py" scene "${2:-1}" ;;
  stop)    pkill -x obs; sleep 2; pgrep -x obs >/dev/null && echo "OBS still running" || echo "OBS stopped" ;;
  status)  wmctrl -lx | awk '{print $3, "|", $2}' | grep -i -E "obs|discord" | sed 's/ - .*discord/ discord/I' | cut -c1-60; pgrep -x obs >/dev/null && echo "obs running" || echo "obs not running";
           echo "active window class: $(xdotool getactivewindow getwindowclassname 2>/dev/null)" ;;
esac
