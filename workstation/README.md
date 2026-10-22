# Streaming workstation (OBS + Discord on a small Ubuntu server)

Scripts used to turn a spare Ubuntu 24.04 server into a stage machine whose output goes into a Beam room (see the main README for the viewer and `sender.py`).
Software only (no GPU): a 2 vCPU / 4 GB server can encode 480p with x264 ultrafast.

| File | Run as | What it does |
|---|---|---|
| `setup.sh` | root | swap file, XFCE desktop with VNC + noVNC bound to 127.0.0.1 only (reach it through an SSH tunnel), OBS, Discord (official .deb), ffmpeg, the Beam CLI (not signed in), user `streamer` |
| `config_obs.sh` | root | OBS profile `BeamLive`: 854x480 at 25 fps, x264 ultrafast, a keyframe every second, MPEG-TS to `udp://127.0.0.1:9000` (the "Start Recording" button), AAC audio |
| `make_overlay.py` + `overlay_assets/` | any | the Beam graphics (background, frame, side panel, LIVE badge, title cards); needs Pillow; copy the PNGs to `/home/streamer/overlay` |
| `scenes.sh` | root | scene collection: Starting soon, Discord (cropped, framed), Game, Be right back, Fullscreen, Whole desktop; desktop-audio capture; a STATUS text read from `~/overlay/status.txt` |
| `obs_remote_setup.sh` + `obs_ctl.py` | root / streamer | OBS remote control on localhost with a random password; `obs_ctl.py scene Fullscreen` switches scenes while OBS stays minimized |
| `stage.sh` | streamer | `prepare` / `live` / `scene N` / `stop` / `status` (OBS minimized, Discord maximized in front) |
| `sender.sh` | streamer | starts `sender.py` on OBS's UDP output (`ROOM=... CHANNEL=... ./sender.sh start`) |

Privacy: the Discord scene crops the server list, channel list (account panel), member list, top bar and message box (default 312/240/75/155 px on a 1280x720 desktop), but the centre of the
window is still shown, so turn on Discord's Streamer Mode and use a voice/stream view. Nothing here logs in to Discord for you.
