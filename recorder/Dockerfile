# Xvfb + ffmpeg x11grab recorder sidecar (Phase 4).
#
# Captures a virtual X display (:99) to recordings/run_<ts>.mp4. Because
# x11grab records PIXELS, the recorded job MUST drive a visible surface onto
# DISPLAY=:99 (review decision). For the tech-debt hero the surface is a LIVE
# SPLIT-SCREEN: an xterm running `tail -f` on the agent log (the reasoning/tool
# calls scroll as the loop runs) on the LEFT, and a browser showing the legible
# coupling graph graphify-out/service-graph.html on the RIGHT — the before→after
# money shot. scripts/record_run.sh wires both surfaces onto :99 before triggering
# the agent so the capture is never black AND the frame CHANGES over time.
#
# This image bundles Xvfb, ffmpeg, a lightweight window manager, a browser, an
# xterm (the live agent-log pane), and a fonts package so rendered text is
# legible. The entrypoint starts Xvfb, tiles the surfaces, then runs ffmpeg; a
# graceful stop sends `q` to ffmpeg to finalize the MP4 moov atom (research §14).
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    SCREEN_W=1280 \
    SCREEN_H=720 \
    SCREEN_D=24 \
    REC_DIR=/recordings

# - xvfb        : the virtual X display
# - ffmpeg      : x11grab capture
# - x11-utils   : xdpyinfo (readiness probe) + xwininfo (mapped-window guard)
# - wmctrl      : place/size windows precisely (tile the split-screen panes)
# - fluxbox     : minimal WM so windows map/decorate (legible capture)
# - chromium    : the visible browser surface (service-graph.html / Linear / PMF)
# - xterm       : the LIVE agent-log pane (`tail -f` of the agent reasoning log)
# - fonts-*     : legible text (the surface is mostly text/graph labels)
# - x11-apps    : xmessage / xclock fallbacks if no browser surface is supplied
# - x11vnc      : OPTIONAL one-time interactive bridge to :99 so a human can log into
#                 Linear once and persist the session into the mounted --user-data-dir
#                 (the authenticated live-Linear ending). Used only by the `login`
#                 verb; never on the default capture path.
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb ffmpeg x11-utils x11-apps wmctrl fluxbox chromium xterm x11vnc \
        fonts-dejavu fonts-liberation ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/recorder
COPY entrypoint.sh /opt/recorder/entrypoint.sh
RUN chmod +x /opt/recorder/entrypoint.sh

VOLUME ["/recordings"]

# Healthcheck: the Xvfb display is up and answering (xdpyinfo succeeds).
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD xdpyinfo -display :99 >/dev/null 2>&1 || exit 1

ENTRYPOINT ["/opt/recorder/entrypoint.sh"]
# Default command keeps the display alive (idle) so the container is "healthy"
# and ready; scripts/record_run.sh drives capture via `docker exec` (start/stop).
CMD ["idle"]
