#!/bin/bash
# Configure OBS (profile + scene collection "BeamLive") and desktop launchers for user `streamer` on the streaming workstation. Run as root on the box.
# OBS output: Custom Output (FFmpeg) -> MPEG-TS over UDP to 127.0.0.1:9000 (a local sender reads it), 854x480, 25 fps, x264 ultrafast zerolatency,
# 800 kbps, keyframe every second (25 frames; 1 s message fragments), AAC 96 kbps. Scene "Game": a looping media file (replace the placeholder) and an optional screen capture.
set -euo pipefail
U=streamer; H=/home/$U
C=$H/.config/obs-studio
mkdir -p $C/basic/profiles/BeamLive $C/basic/scenes $H/videos $H/Desktop

# a placeholder clip so the scene is not empty (replace $H/videos/gameplay.mp4 with the real clip)
if [ ! -f $H/videos/gameplay.mp4 ]; then
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=size=854x480:rate=25" -f lavfi -i "sine=frequency=440:sample_rate=44100" -t 60 \
    -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac $H/videos/gameplay.mp4
fi

cat > $C/global.ini <<'EOF'
[General]
FirstRun=true
Pre19Defaults=false
Pre21Defaults=false
Pre23Defaults=false
Pre24.1Defaults=false
MaxLogs=3
InfoIncrementalUpdateOnly=true
[Basic]
Profile=BeamLive
ProfileDir=BeamLive
SceneCollection=BeamLive
SceneCollectionFile=BeamLive
[BasicWindow]
SysTrayEnabled=false
SysTrayWhenStarted=false
EOF

cat > $C/basic/profiles/BeamLive/basic.ini <<'EOF'
[General]
Name=BeamLive

[Video]
BaseCX=854
BaseCY=480
OutputCX=854
OutputCY=480
FPSType=1
FPSInt=25
ScaleType=bicubic
ColorFormat=NV12
ColorSpace=709
ColorRange=Partial

[Audio]
SampleRate=44100
ChannelSetup=Stereo

[Output]
Mode=Advanced

[AdvOut]
RecType=FFmpeg
FFOutputToFile=false
FFURL=udp://127.0.0.1:9000?pkt_size=1316
FFFormat=mpegts
FFFormatMimeType=video/MP2T
FFVEncoderId=27
FFVEncoder=libx264
FFVBitrate=800
FFVGOPSize=25
FFVCustom=preset=ultrafast tune=zerolatency
FFAEncoderId=86018
FFAEncoder=aac
FFABitrate=96
FFAudioMixes=1
FFIgnoreCompat=false
FFRescale=false
EOF

cat > $C/basic/scenes/BeamLive.json <<EOF
{
  "current_scene": "Game",
  "current_program_scene": "Game",
  "scene_order": [{"name": "Game"}],
  "name": "BeamLive",
  "sources": [
    {"id": "ffmpeg_source", "name": "Gameplay clip", "uuid": "11111111-1111-4111-8111-111111111111", "versioned_id": "ffmpeg_source", "enabled": true, "muted": false, "volume": 1.0,
     "settings": {"local_file": "$H/videos/gameplay.mp4", "is_local_file": true, "looping": true, "close_when_inactive": false, "restart_on_activate": true, "hw_decode": false}},
    {"id": "xshm_input", "name": "Screen capture", "uuid": "22222222-2222-4222-8222-222222222222", "versioned_id": "xshm_input", "enabled": true, "muted": false, "volume": 1.0,
     "settings": {"screen": 0, "show_cursor": true}},
    {"id": "scene", "name": "Game", "uuid": "33333333-3333-4333-8333-333333333333", "versioned_id": "scene", "enabled": true, "muted": false, "volume": 1.0,
     "settings": {"id_counter": 2, "custom_size": false, "items": [
        {"name": "Gameplay clip", "source_uuid": "11111111-1111-4111-8111-111111111111", "id": 1, "visible": true, "locked": false,
         "pos": {"x": 0.0, "y": 0.0}, "scale": {"x": 1.0, "y": 1.0}, "rot": 0.0, "align": 5, "bounds_type": 2, "bounds": {"x": 854.0, "y": 480.0}, "bounds_align": 0},
        {"name": "Screen capture", "source_uuid": "22222222-2222-4222-8222-222222222222", "id": 2, "visible": false, "locked": false,
         "pos": {"x": 0.0, "y": 0.0}, "scale": {"x": 1.0, "y": 1.0}, "rot": 0.0, "align": 5, "bounds_type": 2, "bounds": {"x": 854.0, "y": 480.0}, "bounds_align": 0}]}}
  ],
  "groups": [], "quick_transitions": [], "transitions": []
}
EOF

# desktop launchers
cat > $H/Desktop/OBS-BeamLive.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=OBS (BeamLive)
Exec=obs --profile BeamLive --collection BeamLive --disable-shutdown-check
Terminal=false
EOF
cat > $H/Desktop/Discord.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Discord (no GPU)
Exec=/usr/local/bin/discord-nogpu
Terminal=false
EOF
cat > $H/Desktop/Terminal.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Terminal
Exec=xfce4-terminal
Terminal=false
EOF
chmod +x $H/Desktop/*.desktop
chown -R $U:$U $C $H/videos $H/Desktop
echo configured
