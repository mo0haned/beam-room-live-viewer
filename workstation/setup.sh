#!/bin/bash
# Streaming workstation on a spare Ubuntu 24.04 server (run as root on the box): XFCE desktop reachable through VNC + noVNC (both bound to 127.0.0.1 only;
# reach it with an SSH tunnel), OBS Studio, Discord (official .deb), ffmpeg, the Beam CLI (not signed in) and the livetest scripts for user `streamer`.
# Nothing is opened to the internet: VNC (5901) and noVNC (6080) listen on 127.0.0.1 only, so reaching the desktop requires an SSH login to the box. Safe to re-run.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a NEEDRESTART_SUSPEND=1
U=streamer
H=/home/$U

echo "== swap"
if ! swapon --show | grep -q swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
free -m | sed -n 1,3p

echo "== packages"
apt-get update -y >/dev/null
apt-get install -y --no-install-recommends xfce4 xfce4-terminal dbus-x11 tigervnc-standalone-server tigervnc-common novnc websockify obs-studio ffmpeg \
  pulseaudio pavucontrol xdg-utils fonts-dejavu-core curl ca-certificates python3 openssl >/dev/null

echo "== discord (official .deb)"
if ! command -v discord >/dev/null; then
  curl -fsSL -o /tmp/discord.deb "https://discord.com/api/download?platform=linux&format=deb"
  apt-get install -y /tmp/discord.deb >/dev/null
fi

echo "== user $U"
id $U >/dev/null 2>&1 || useradd -m -s /bin/bash $U
mkdir -p $H/.vnc $H/livetest $H/.local/bin
cat > $H/.vnc/xstartup <<'XS'
#!/bin/sh
unset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
pulseaudio --start --exit-idle-time=-1 2>/dev/null || true
exec startxfce4
XS
chmod +x $H/.vnc/xstartup
# launchers that work without a GPU
cat > /usr/local/bin/discord-nogpu <<'L'
#!/bin/sh
exec discord --disable-gpu --disable-software-rasterizer "$@"
L
chmod +x /usr/local/bin/discord-nogpu
chown -R $U:$U $H

echo "== beam cli (not signed in)"
if [ ! -x $H/.local/bin/beam ]; then
  su - $U -c "curl -fsSL https://cdn.b1m.ai/cli/install.sh -o /tmp/beam_install.sh && BEAM_INSTALL_DIR=$H/.local/bin BEAM_SKIP_ONBOARDING=1 sh /tmp/beam_install.sh >/dev/null && $H/.local/bin/beam --version | head -n 1"
fi
grep -q '.local/bin' $H/.bashrc || echo 'export PATH=$HOME/.local/bin:$PATH' >> $H/.bashrc

echo "== services (localhost only)"
cat > /etc/systemd/system/streamer-vnc.service <<EOF
[Unit]
Description=VNC desktop for the streaming workstation (localhost only)
After=network.target
[Service]
User=$U
Environment=HOME=$H
ExecStartPre=-/usr/bin/vncserver -kill :1
ExecStart=/usr/bin/vncserver :1 -localhost yes -geometry 1280x720 -depth 24 -fg -SecurityTypes None
ExecStop=/usr/bin/vncserver -kill :1
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
cat > /etc/systemd/system/streamer-novnc.service <<EOF
[Unit]
Description=noVNC web client for the streaming workstation (localhost only)
After=streamer-vnc.service
[Service]
ExecStart=/usr/bin/websockify --web /usr/share/novnc 127.0.0.1:6080 127.0.0.1:5901
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now streamer-vnc.service streamer-novnc.service >/dev/null 2>&1
sleep 5

echo "== verify"
systemctl is-active streamer-vnc.service streamer-novnc.service
ss -ltn | awk 'NR==1 || /:(5901|6080)\b/'
command -v obs && obs --version 2>&1 | head -n 1
dpkg -l discord | tail -n 1 | awk '{print $2, $3}'
echo "Desktop: no VNC password (localhost only); the SSH tunnel is the access control."
