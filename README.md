# Beam room live viewer

Watch a live video that is sent through a Beam room message channel (about 1 MB/s of small encrypted messages, no web server in between).

When the host is streaming, a 480p video loops through a Beam room: the streamer sends it as small encrypted messages (about 100 KB each, one per second) and your computer plays
it from what Beam delivers to you. Nothing is streamed over a normal web server. You run a small local page that only reads what your Beam agent receives.

The room ID below is only valid while the host has the room open (they run it for a test and close it afterwards); ask them if it is live.

You need: Linux or macOS, Python 3.9+, a Beam account (free sign-in at the Beam login page), and an invitation file from the host. **Ask the host for
the invitation file privately; do not post it anywhere. It is the key to the room.**


## Quick start with Docker (no install on your machine)

    docker build -t beam-live-viewer https://github.com/mo0haned/beam-room-live-viewer.git
    docker run --rm -it -p 8820:8820 -v beam-live:/data -v "$PWD/invite.json:/invite.json:ro" beam-live-viewer ROOM_ID

Then open http://127.0.0.1:8820/. The first run prints a Beam sign-in link and code (approve it in a browser); the `beam-live` volume remembers your
login and agent, so later runs only need the room ID. Instead of the interactive sign-in you can pass a Beam API key: `-e BEAM_API_KEY`.
Set `-e LABEL=my-name` to name your machine in Beam. The invitation file is only needed the first time.

## Steps (without Docker)

1. Install the Beam CLI (read the script first if you like: https://cdn.b1m.ai/cli/install.sh):

       curl -fsSL https://cdn.b1m.ai/cli/install.sh | sh

2. Sign in (it prints a link and a code; open the link and approve):

       beam auth login

3. Start your agent for this machine. If this asks for an organization or a key, stop and tell the host:

       beam agent connect --label my-laptop

4. Join the room with the invitation file the host sent you:

       beam room join btr_room_doup3kevyymohmm3ikhmef65ne --invitation-file ./invite.json

5. Run the viewer and open the page it prints (http://127.0.0.1:8820/):

       python3 viewer.py --room btr_room_doup3kevyymohmm3ikhmef65ne

The page shows the video, a counter of received / missing fragments, and the delay of each fragment. Playback starts after 4 fragments (about 4 s).
Messages are live-only: you see the stream from the moment you start the viewer, and you miss what was sent before. If the host is not streaming yet,
it says "waiting for the first fragment".

## Notes

- The delay column assumes your clock and the streamer's clock are both set by NTP (normal on laptops), so treat it as approximate.
- The page loads the hls.js player from cdnjs.cloudflare.com, so it needs internet access in the browser.
- To leave: stop the viewer (Ctrl+C), then `beam room leave btr_room_doup3kevyymohmm3ikhmef65ne`, then `beam agent stop`.
- Not tested from a second person's machine yet: steps 3 and 4 are the likely places to need a fix.
