#!/bin/sh
# Joins a Beam room and serves the viewer page on :8820.
#   argument or $ROOM        the room id (required)
#   /invite.json or $INVITATION   the invitation (file path or token), needed the first time you join
#   $BEAM_API_KEY            optional: enrol this container with a Beam API key instead of the interactive sign-in
#   $LABEL                   name of this machine in Beam (default: docker-viewer)
set -eu
ROOM="${1:-${ROOM:-}}"
[ -n "$ROOM" ] || { echo "usage: docker run ... IMAGE ROOM_ID" >&2; exit 2; }
export HOME=/data
mkdir -p /data

# 1. identity: an API key, or the interactive device sign-in (prints a link and a code to approve in a browser)
if [ -z "${BEAM_API_KEY:-}" ] && ! beam whoami >/dev/null 2>&1; then
  echo "== Sign in to Beam: open the link below and approve the code (this container waits)"
  beam auth login
fi

# 2. this machine's agent
if ! beam agent status 2>/dev/null | grep -q connected; then
  echo "== Connecting this machine to Beam as ${LABEL:-docker-viewer}"
  beam agent connect --label "${LABEL:-docker-viewer}"
fi
beam agent start >/dev/null 2>&1 || true

# 3. the room (skipped when this machine is already a member)
if ! beam room "$ROOM" show >/dev/null 2>&1; then
  echo "== Joining room $ROOM"
  if [ -f /invite.json ]; then beam room join "$ROOM" --invitation-file /invite.json
  elif [ -n "${INVITATION:-}" ]; then beam room join "$ROOM" --invitation-token "$INVITATION"
  else echo "No invitation found: mount it at /invite.json or set INVITATION" >&2; exit 3; fi
fi

echo "== Viewer page: http://127.0.0.1:8820/  (map the port with -p 8820:8820)"
exec python3 /app/viewer.py --room "$ROOM" --bind 0.0.0.0 --port 8820
