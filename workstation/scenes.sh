#!/bin/bash
# Builds the OBS scene collection "BeamLive" on the streaming workstation (run as root on the box; upload overlay_assets/*.png to /home/streamer/overlay first).
#   Scenes:  "Starting soon" | "Discord" | "Game" | "Be right back"
#   "Discord": the cropped capture of the maximized Discord window sits in the glowing frame (16,56 570x384); the crop removes the server list, channel list (with
#             the account panel), member list, top bar and the bottom message box. The overlay adds the Beam logo, a LIVE badge and a side panel whose STATUS text is
#             read from /home/streamer/overlay/status.txt (the Beam sender can write chunk delay there).
#   "Game":   the same layout with the looping clip.
#   "Fullscreen": the same cropped Discord content filling the whole frame (16:9 crop), only a small logo chip and a LIVE badge on top.   [F5]
#   "Whole desktop (shows everything)": the uncropped desktop, nothing hidden: only for content that is safe to show.   [F6]
# Crop in pixels removed from the 1280x720 desktop. Default LEFT=312 (server list 72 + channel list 240), RIGHT=240 (members), TOP=75 (panel 27 + header 48),
# BOTTOM=155 (message box; makes the region the frame's 570:384 shape). Change:  obs_box_discord_scene.sh LEFT RIGHT TOP BOTTOM   (close OBS first).
set -euo pipefail
U=streamer; H=/home/$U
L=${1:-312}; R=${2:-240}; T=${3:-75}; B=${4:-155}
F=$H/.config/obs-studio/basic/scenes/BeamLive.json
pgrep -u $U -x obs >/dev/null && { echo "close OBS first (it rewrites the scene file on exit)"; exit 1; }
mkdir -p $H/overlay
[ -f $H/overlay/status.txt ] || printf 'waiting for the stream\n\nchunk delay\n--\n' > $H/overlay/status.txt
chown -R $U:$U $H/overlay
python3 - "$F" "$H" "$L" "$R" "$T" "$B" <<'PY'
import json, sys
f, home, L, R, T, B = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
n = [0]
def uid():
    n[0] += 1; i = f"{n[0]:x}"[-1]
    return f"{i*8}-{i*4}-4{i*3}-8{i*3}-{i*12}"
def src(id_, name, settings, **kw):
    return {"id": id_, "name": name, "uuid": uid(), "versioned_id": id_, "enabled": True, "muted": False, "volume": 1.0, "settings": settings, **kw}
img = lambda name, p: src("image_source", name, {"file": f"{home}/overlay/{p}"})
B169 = max(0, 720 - T - int((1280 - L - R) * 9 / 16))      # bottom crop that makes the region exactly 16:9 for the fullscreen scene
S = {
  "bg": img("Background", "bg.png"), "overlay": img("Overlay", "overlay.png"), "start": img("Starting soon card", "starting.png"), "brb": img("BRB card", "brb.png"),
  "clip": src("ffmpeg_source", "Gameplay clip", {"local_file": f"{home}/videos/gameplay.mp4", "is_local_file": True, "looping": True, "close_when_inactive": False, "restart_on_activate": True, "hw_decode": False}),
  "disc": src("xshm_input", "Discord (cropped screen)", {"screen": 0, "show_cursor": False, "advanced": True, "cut_left": L, "cut_right": R, "cut_top": T, "cut_bot": B}),
  "disc169": src("xshm_input", "Discord (cropped 16:9)", {"screen": 0, "show_cursor": False, "advanced": True, "cut_left": L, "cut_right": R, "cut_top": T, "cut_bot": B169}),
  "desk": src("xshm_input", "Whole desktop (shows everything)", {"screen": 0, "show_cursor": True}),
  "ovmin": img("Overlay minimal", "overlay_min.png"),
  "status": src("text_ft2_source", "Status text", {"from_file": True, "text_file": f"{home}/overlay/status.txt", "font": {"face": "DejaVu Sans", "size": 15, "style": "Bold", "flags": 1},
                "color1": 4294967295, "color2": 4294967295, "word_wrap": True, "custom_width": 204, "antialiasing": True}),
}
def item(s, i, x=0.0, y=0.0, bounds=None, visible=True):
    d = {"name": s["name"], "source_uuid": s["uuid"], "id": i, "visible": visible, "locked": False, "pos": {"x": x, "y": y}, "scale": {"x": 1.0, "y": 1.0}, "rot": 0.0, "align": 5,
         "bounds_type": 0, "bounds": {"x": 0.0, "y": 0.0}, "bounds_align": 0}
    if bounds:
        d.update(bounds_type=2, bounds={"x": float(bounds[0]), "y": float(bounds[1])})
    return d
def scene(name, items, key):
    # F1..F4 select the scene (global hotkeys; stage.sh scene <n> sends the key with xdotool, so OBS can stay minimized)
    return src("scene", name, {"id_counter": len(items), "custom_size": False, "items": items}, hotkeys={"OBSBasic.SelectScene": [{"key": f"OBS_KEY_F{key}"}]})
full = (854, 480)
scenes = [
  scene("Starting soon", [item(S["start"], 1, bounds=full)], 1),
  scene("Discord", [item(S["bg"], 1, bounds=full), item(S["disc"], 2, 16, 56, (570, 384)), item(S["overlay"], 3, bounds=full), item(S["status"], 4, 618, 254)], 2),
  scene("Game",    [item(S["bg"], 1, bounds=full), item(S["clip"], 2, 16, 56, (570, 384)), item(S["overlay"], 3, bounds=full), item(S["status"], 4, 618, 254)], 3),
  scene("Be right back", [item(S["brb"], 1, bounds=full)], 4),
  scene("Fullscreen", [item(S["disc169"], 1, bounds=full), item(S["ovmin"], 2, bounds=full)], 5),
  scene("Whole desktop (shows everything)", [item(S["desk"], 1, bounds=full), item(S["ovmin"], 2, bounds=full)], 6),
]
# audio: capture whatever plays on the box's sound output (Discord's voice/stream audio goes to the PulseAudio sink auto_null; its monitor is the capture device)
audio = {"prev_ver": 536870912, "name": "Desktop Audio", "uuid": uid(), "id": "pulse_output_capture", "versioned_id": "pulse_output_capture", "settings": {"device_id": "auto_null.monitor"},
         "mixers": 255, "sync": 0, "flags": 0, "volume": 1.0, "balance": 0.5, "enabled": True, "muted": False, "push-to-mute": False, "push-to-mute-delay": 0,
         "push-to-talk": False, "push-to-talk-delay": 0, "hotkeys": {}, "deinterlace_mode": 0, "deinterlace_field_order": 0, "monitoring_type": 0, "private_settings": {}}
json.dump({"DesktopAudioDevice1": audio, "current_scene": "Discord", "current_program_scene": "Discord", "scene_order": [{"name": s["name"]} for s in scenes], "name": "BeamLive",
           "sources": list(S.values()) + scenes, "groups": [], "quick_transitions": [], "transitions": []}, open(f, "w"), indent=1)
print(f"scenes written: {[s['name'] for s in scenes]} (Discord crop L{L} R{R} T{T} B{B})")
PY
chown $U:$U $F
