# Beam room live viewer: the Beam CLI + the local viewer page in one image.
#   docker build -t beam-live-viewer https://github.com/mo0haned/beam-room-live-viewer.git
#   docker run --rm -it -p 8820:8820 -v beam-live:/data -v $PWD/invite.json:/invite.json:ro beam-live-viewer ROOM_ID
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*
# the official installer, into /usr/local/bin (its script: https://cdn.b1m.ai/cli/install.sh)
RUN BEAM_INSTALL_DIR=/usr/local/bin BEAM_SKIP_ONBOARDING=1 sh -c "$(curl -fsSL https://cdn.b1m.ai/cli/install.sh)" \
    && beam --version
WORKDIR /app
COPY viewer.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh
ENV HOME=/data
VOLUME /data
EXPOSE 8820
ENTRYPOINT ["/app/entrypoint.sh"]
