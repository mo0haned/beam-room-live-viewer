# Beam room live viewer

Watch a live video that is sent through a Beam room message channel (about 1 MB/s of small encrypted messages, no web server in between).

When the host is streaming, a 480p video loops through a Beam room: the streamer sends it as small encrypted messages (about 100 KB each, one per second) and your computer plays
it from what Beam delivers to you. Nothing is streamed over a normal web server. You run a small local page that only reads what your Beam agent receives.

The room ID below is only valid while the host has the room open (they run it for a test and close it afterwards); ask them if it is live.

You need: Linux or macOS, Python 3.9+, a Beam account (free sign-in at the Beam login page), and an invitation file from the host. The invitation is `invite.json` in this repository (single use, valid until 23:17 UTC on 2026-10-22); if it is used up or expired, ask the host for a new one. It is the key to the room, so treat it like one.


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


## Broadcasting (the sender side)

The viewer above only receives. To send your own video into the room's message channel:

1. Join the room as a member with the `publish` grant on the video channel (the host gives you an invitation for that).
2. Make the video available as MPEG-TS with a **keyframe every second**:
   - **From OBS:** Settings, Output, Advanced, Recording type **Custom Output (FFmpeg)**, "Output to URL" `udp://127.0.0.1:9000?pkt_size=1316`, container `mpegts`,
     video encoder libx264 (`preset=ultrafast tune=zerolatency`), keyframe interval 25 frames at 25 fps (1 s), about 800 kbps at 854x480, audio AAC. Then press **Start Recording**.
   - **From a file:** nothing to do; the sender plays it in real time (`--loop` repeats it). Encode it with `-g 25 -keyint_min 25 -sc_threshold 0`.
3. Run the sender (needs ffmpeg and the signed-in Beam CLI):

       python3 sender.py --room ROOM_ID --channel CHANNEL_ID --source 'udp://127.0.0.1:9000?fifo_size=5000000&overrun_nonfatal=1' --out ./out --parallel 12 --max-age 8

   Fragments older than `--max-age` seconds are dropped instead of building a backlog. `--status-file FILE` writes the last publish time into a text file (OBS can show it).

Measured on a 30 s clip with the sender on one continent and receivers on two others: about 1-3 s from "fragment complete" to "arrived", no fragment lost; a home connection that
times out to the Beam coordinator made the delay and loss much worse. Messages are live-only, so a viewer sees the stream from the moment it starts listening.

## Running a stage machine

`workstation/` has the scripts that turn a small Ubuntu server into a streaming workstation (OBS scenes with Beam graphics, Discord, remote scene control, and the sender) - see `workstation/README.md`.

## Notes

- The delay column assumes your clock and the streamer's clock are both set by NTP (normal on laptops), so treat it as approximate.
- The page loads the hls.js player from cdnjs.cloudflare.com, so it needs internet access in the browser.
- To leave: stop the viewer (Ctrl+C), then `beam room leave btr_room_doup3kevyymohmm3ikhmef65ne`, then `beam agent stop`.
- Not tested from a second person's machine yet: steps 3 and 4 are the likely places to need a fix.
