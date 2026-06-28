#!/usr/bin/env bash
#
# entrypoint.sh — Xvfb + ffmpeg x11grab recorder control surface (Phase 4).
#
# The container runs `idle` as its long-lived command: it brings up Xvfb on :99
# (and a minimal WM) and stays healthy/ready. scripts/record_run.sh then drives
# capture from the host via `docker exec`:
#
#   docker exec recorder /opt/recorder/entrypoint.sh surface-html /recordings/x.html
#   docker exec recorder /opt/recorder/entrypoint.sh start run_<ts>.mp4
#   ...trigger the agent job (host)...
#   docker exec recorder /opt/recorder/entrypoint.sh stop          # graceful q -> moov
#
# Because x11grab records PIXELS, a visible surface MUST be painted onto :99
# BEFORE `start` (review decision) or the capture is a flat black frame. The
# `surface-*` verbs paint that surface; `start` refuses to begin if the display
# has no mapped client window (guard against a black recording).
set -euo pipefail

DISPLAY_NUM="${DISPLAY:-:99}"
SCREEN_W="${SCREEN_W:-1280}"
SCREEN_H="${SCREEN_H:-720}"
SCREEN_D="${SCREEN_D:-24}"
REC_DIR="${REC_DIR:-/recordings}"
FF_PIDFILE=/tmp/ffmpeg.pid
XVFB_PIDFILE=/tmp/xvfb.pid
WM_PIDFILE=/tmp/fluxbox.pid
SURFACE_PIDFILE=/tmp/surface.pid

log() { echo "[recorder] $*" >&2; }

# --- bring up Xvfb (idempotent) ---------------------------------------------
start_xvfb() {
  if xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1; then
    log "Xvfb already up on $DISPLAY_NUM"
    return 0
  fi
  log "starting Xvfb on $DISPLAY_NUM (${SCREEN_W}x${SCREEN_H}x${SCREEN_D})"
  Xvfb "$DISPLAY_NUM" -screen 0 "${SCREEN_W}x${SCREEN_H}x${SCREEN_D}" -ac -nolisten tcp >/tmp/xvfb.log 2>&1 &
  echo $! > "$XVFB_PIDFILE"
  # wait for the display to answer
  for _ in $(seq 1 50); do
    xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1 && break
    sleep 0.2
  done
  xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1 || { log "Xvfb failed to come up"; cat /tmp/xvfb.log >&2 || true; return 1; }
  # minimal WM so windows map + get decorations (legible capture)
  if [ ! -f "$WM_PIDFILE" ] || ! kill -0 "$(cat "$WM_PIDFILE" 2>/dev/null)" 2>/dev/null; then
    DISPLAY="$DISPLAY_NUM" fluxbox >/tmp/fluxbox.log 2>&1 &
    echo $! > "$WM_PIDFILE"
    sleep 0.5
  fi
}

# --- does the display have a real client window mapped? (non-black guard) ----
has_mapped_window() {
  # count client windows under the root; >0 means something is painted.
  local n
  n="$(DISPLAY="$DISPLAY_NUM" xwininfo -root -children 2>/dev/null \
        | grep -cE '0x[0-9a-f]+ ' || true)"
  [ "${n:-0}" -gt 0 ]
}

# --- paint a browser surface (URL or local HTML file) ------------------------
# $2 (optional) "right" tiles the browser to the right HALF of the screen (for the
# split-screen); default is full-screen kiosk.
#
# GLO-14 P3: when CHROMIUM_USER_DATA_DIR is set (a bind-mounted, PERSISTENT and
# AUTHENTICATED Chromium profile — see docker-compose.yml + scripts/record_run.sh's
# TICKET_LIVE_URL=1 path), Chromium launches WITH `--user-data-dir=<that dir>` so a
# real logged-in Linear session is carried into the capture (the live authenticated
# Linear ending). With NO such dir set (the reproducible DEFAULT), Chromium launches
# throwaway/sessionless exactly as before — so the default `file://` snapshot ending
# is unchanged and never depends on any host-held session. The profile dir is
# gitignored (no session secrets committed — AGENTS.md rule 3/8).
launch_browser() {
  local target="$1"
  local where="${2:-full}"
  # kill any prior browser surface
  if [ -f "$SURFACE_PIDFILE" ]; then kill "$(cat "$SURFACE_PIDFILE")" 2>/dev/null || true; fi

  local w="$SCREEN_W" x=0
  local args=(--start-maximized --kiosk)
  if [ "$where" = "right" ]; then
    w=$(( SCREEN_W / 2 )); x=$(( SCREEN_W - w ))
    # not kiosk when tiled (kiosk forces fullscreen and ignores geometry)
    args=(--window-position="${x},0")
  fi

  # Persistent authenticated profile (GLO-14 P3, OPTIONAL): only when a profile dir
  # is mounted. Default runs leave this empty -> sessionless throwaway browser.
  if [ -n "${CHROMIUM_USER_DATA_DIR:-}" ]; then
    mkdir -p "$CHROMIUM_USER_DATA_DIR" 2>/dev/null || true
    args+=(--user-data-dir="$CHROMIUM_USER_DATA_DIR")
    log "using PERSISTENT Chromium profile --user-data-dir=$CHROMIUM_USER_DATA_DIR (authenticated-session path)"
  fi

  log "painting browser surface: $target (where=$where, ${w}x${SCREEN_H}+${x})"
  DISPLAY="$DISPLAY_NUM" chromium \
      --no-sandbox --disable-gpu --disable-dev-shm-usage \
      --no-first-run --no-default-browser-check --disable-translate \
      --window-size="${w},${SCREEN_H}" "${args[@]}" \
      "$target" >/tmp/chromium.log 2>&1 &
  echo $! > "$SURFACE_PIDFILE"
  # give the renderer time to paint
  sleep 6
  if [ "$where" = "right" ]; then
    # nudge geometry with wmctrl in case the WM ignored the launch position
    DISPLAY="$DISPLAY_NUM" wmctrl -l >/dev/null 2>&1 && \
      DISPLAY="$DISPLAY_NUM" wmctrl -r :ACTIVE: -e "0,${x},0,${w},${SCREEN_H}" 2>/dev/null || true
  fi
}

# --- paint a LIVE terminal pane tailing a log file (the agent reasoning) ------
# This is the half of the split-screen that CHANGES over time: as the agent loop
# appends reasoning/tool-call output to LOGFILE, `tail -f` scrolls it on screen so
# the recording is demonstrably non-static. Tiled to the LEFT half by default.
TERM_PIDFILE=/tmp/term.pid
launch_log_terminal() {
  local logfile="$1"
  local title="${2:-agent}"
  if [ -f "$TERM_PIDFILE" ]; then kill "$(cat "$TERM_PIDFILE")" 2>/dev/null || true; fi
  # ensure the file exists so tail -f has something to follow immediately
  : > "$logfile" 2>/dev/null || true
  local w; w=$(( SCREEN_W / 2 ))
  log "painting live log terminal: tail -f $logfile (left ${w}x${SCREEN_H})"
  # geometry in CHARACTER cells is approximate; we resize precisely with wmctrl
  # after map. A dark bg + bright fg keeps the scrolling text legible on capture.
  DISPLAY="$DISPLAY_NUM" xterm \
      -geometry 100x44+0+0 \
      -bg '#0f1721' -fg '#d8e2ec' \
      -fa 'DejaVu Sans Mono' -fs 11 \
      -T "sovereign-cto: $title (live)" \
      -e bash -lc "printf '\033]0;sovereign-cto %s (live)\007' '$title'; \
                   echo '=== sovereign-cto :: live agent log ($title) ==='; \
                   echo '=== watching $logfile ==='; echo; \
                   exec tail -n +1 -f '$logfile'" \
      >/tmp/xterm.log 2>&1 &
  echo $! > "$TERM_PIDFILE"
  sleep 2
  DISPLAY="$DISPLAY_NUM" wmctrl -l >/dev/null 2>&1 && \
    DISPLAY="$DISPLAY_NUM" wmctrl -r :ACTIVE: -e "0,0,0,${w},${SCREEN_H}" 2>/dev/null || true
}

# --- paint the SPLIT-SCREEN hero surface: live log (left) + graph (right) -----
launch_split() {
  local logfile="$1"; local target="$2"; local title="${3:-tech-debt audit}"
  log "painting split-screen: live log terminal (left) + browser graph (right)"
  launch_log_terminal "$logfile" "$title"
  launch_browser "$target" right
  # re-assert the terminal geometry (the browser map can steal focus/placement)
  local w; w=$(( SCREEN_W / 2 ))
  DISPLAY="$DISPLAY_NUM" wmctrl -l 2>/dev/null | grep -i "live" | head -1 | awk '{print $1}' | \
    while read -r wid; do
      DISPLAY="$DISPLAY_NUM" wmctrl -i -r "$wid" -e "0,0,0,${w},${SCREEN_H}" 2>/dev/null || true
    done
  sleep 1
}

# --- navigate the RIGHT-pane browser to a URL (close the file->ticket loop) ---
# P0 ending: after the run files the [Brownfield]/[Product] ticket, point the
# right pane at the filed Linear ticket so the recording visibly shows the ticket
# appearing in the browser. We reuse launch_browser's "right" tiling so the layout
# matches the split-screen the run was captured with (the left log pane stays put).
navigate_url() {
  local url="$1"
  [ -n "$url" ] || { log "navigate: no URL given"; return 2; }
  log "navigating right-pane browser to filed ticket: $url"
  launch_browser "$url" right
}

# --- paint a plain text banner (fallback surface, never black) ---------------
launch_banner() {
  local msg="${1:-Sovereign CTO — recording}"
  if [ -f "$SURFACE_PIDFILE" ]; then kill "$(cat "$SURFACE_PIDFILE")" 2>/dev/null || true; fi
  log "painting text banner surface"
  DISPLAY="$DISPLAY_NUM" xmessage -center -bg '#0f1721' -fg '#e8543f' \
      -fn '-*-fixed-bold-*-*-*-24-*-*-*-*-*-*-*' "$msg" >/tmp/xmessage.log 2>&1 &
  echo $! > "$SURFACE_PIDFILE"
  sleep 1.5
}

# --- start ffmpeg x11grab capture --------------------------------------------
start_capture() {
  local name="${1:-run_$(date +%Y%m%d_%H%M%S).mp4}"
  mkdir -p "$REC_DIR"
  local out="$REC_DIR/$name"

  # GUARD: refuse to start a black recording — a visible surface must be painted.
  if ! has_mapped_window; then
    log "REFUSING to start: no mapped client window on $DISPLAY_NUM."
    log "Paint a surface first: entrypoint.sh surface-html <file> | surface-url <url> | surface-banner"
    return 3
  fi

  if [ -f "$FF_PIDFILE" ] && kill -0 "$(cat "$FF_PIDFILE" 2>/dev/null)" 2>/dev/null; then
    log "capture already running (pid $(cat "$FF_PIDFILE"))"
    return 0
  fi

  log "starting ffmpeg x11grab -> $out"
  # We DRIVE ffmpeg's stdin via a named fifo so a `q` write stops it gracefully
  # (which finalizes the moov atom — research §14). A holder process keeps the
  # fifo's write end open so ffmpeg's stdin never hits EOF before we send `q`.
  rm -f /tmp/ff_in
  mkfifo /tmp/ff_in
  # holder: keep the write end open until stop time (sleep, then exit on demand).
  sleep infinity > /tmp/ff_in &
  echo $! > /tmp/ff_holder.pid
  ffmpeg -y -f x11grab -draw_mouse 0 -framerate 15 \
      -video_size "${SCREEN_W}x${SCREEN_H}" -i "$DISPLAY_NUM" \
      -pix_fmt yuv420p -vcodec libx264 -preset veryfast -crf 24 \
      -movflags +faststart "$out" \
      < /tmp/ff_in >/tmp/ffmpeg.log 2>&1 &
  echo $! > "$FF_PIDFILE"
  echo "$out" > /tmp/last_output
  sleep 1
  kill -0 "$(cat "$FF_PIDFILE")" 2>/dev/null || { log "ffmpeg failed to start"; cat /tmp/ffmpeg.log >&2 || true; return 1; }
  log "capture running (pid $(cat "$FF_PIDFILE")), output $out"
}

# --- stop ffmpeg gracefully (q -> finalize moov atom) ------------------------
stop_capture() {
  if [ ! -f "$FF_PIDFILE" ]; then log "no capture running"; return 0; fi
  local pid; pid="$(cat "$FF_PIDFILE")"
  if ! kill -0 "$pid" 2>/dev/null; then log "capture pid $pid not alive"; rm -f "$FF_PIDFILE"; return 0; fi
  log "stopping capture gracefully (q -> moov finalize)"
  # First try ffmpeg's interactive 'q' on its stdin fifo, then release the holder
  # so stdin EOFs. If that doesn't land within 3s (ffmpeg only polls stdin keys
  # on some builds), send SIGINT — ffmpeg's documented clean shutdown that writes
  # the same moov trailer. Either path finalizes a valid, seekable MP4.
  if [ -p /tmp/ff_in ]; then printf 'q\n' > /tmp/ff_in 2>/dev/null || true; fi
  if [ -f /tmp/ff_holder.pid ]; then kill "$(cat /tmp/ff_holder.pid)" 2>/dev/null || true; fi
  for _ in $(seq 1 15); do kill -0 "$pid" 2>/dev/null || break; sleep 0.2; done
  if kill -0 "$pid" 2>/dev/null; then
    log "sending SIGINT (graceful finalize — writes the moov trailer)"
    kill -INT "$pid" 2>/dev/null || true
    for _ in $(seq 1 50); do kill -0 "$pid" 2>/dev/null || break; sleep 0.2; done
  fi
  rm -f "$FF_PIDFILE" /tmp/ff_in /tmp/ff_holder.pid
  log "capture stopped; output: $(cat /tmp/last_output 2>/dev/null || echo '?')"
}

# --- snapshot a single frame (for the non-blank check / debugging) -----------
snapshot() {
  local out="${1:-/recordings/frame.png}"
  ffmpeg -y -f x11grab -video_size "${SCREEN_W}x${SCREEN_H}" -i "$DISPLAY_NUM" \
      -frames:v 1 "$out" >/tmp/snapshot.log 2>&1
  log "snapshot -> $out"
}

cmd="${1:-idle}"; shift || true
case "$cmd" in
  idle)
    start_xvfb
    log "idle: Xvfb up on $DISPLAY_NUM, ready for docker exec control. Sleeping."
    # keep PID 1 alive; the WM/Xvfb run in the background.
    exec tail -f /dev/null
    ;;
  surface-url)     start_xvfb; launch_browser "$1" ;;
  # navigate the right-pane browser to a URL (P0 file->ticket ending)
  #   navigate <url>
  navigate)        start_xvfb; navigate_url "$1" ;;
  surface-html)    start_xvfb; launch_browser "file://$1" ;;
  # GLO-14 P3 / D-2: paint the read-only mem0 memory card (a local file:// HTML the
  # host renders via scripts/render_memory_card.py). Same throwaway/no-auth path as
  # surface-html — kept as a NAMED verb so the montage step reads self-documenting.
  surface-memory)  start_xvfb; launch_browser "file://$1" "${2:-full}" ;;
  surface-banner)  start_xvfb; launch_banner "${1:-Sovereign CTO — recording}" ;;
  # split-screen hero: live agent-log terminal (left) + graph html (right)
  #   surface-split <logfile> <html-file> [title]
  surface-split)   start_xvfb; launch_split "$1" "file://$2" "${3:-tech-debt audit}" ;;
  # live log terminal only (left pane); used to attach the log after the browser
  #   surface-logterm <logfile> [title]
  surface-logterm) start_xvfb; launch_log_terminal "$1" "${2:-agent}" ;;
  start)           start_xvfb; start_capture "${1:-}" ;;
  stop)            stop_capture ;;
  # GLO-14 P3: OPTIONAL one-time interactive login to persist a real Linear session
  # into the mounted --user-data-dir (the authenticated live-Linear ending). Launches
  # Chromium (full screen, persistent profile) at the given URL, then bridges :99 over
  # VNC (5900) so a human can SEE and CLICK to log in. The Linux Chromium writes the
  # session cookie into /recorder-profile itself — so the recording reuses it natively
  # (a macOS-host Chrome profile would NOT decrypt under Linux Chromium). One-shot only:
  #   docker compose run --rm -p 5900:5900 -e CHROMIUM_USER_DATA_DIR=/recorder-profile \
  #       recorder login
  # then connect a VNC viewer to localhost:5900 (macOS: Finder → Go → Connect to
  # Server → vnc://localhost:5900), log into Linear, and Ctrl-C when done.
  login)
    if [ -z "${CHROMIUM_USER_DATA_DIR:-}" ]; then
      echo "login: refusing — set CHROMIUM_USER_DATA_DIR (e.g. /recorder-profile) so the session persists" >&2
      exit 2
    fi
    start_xvfb
    # A prior container that held this profile can leave a stale SingletonLock/Socket
    # behind; the new Chromium then sees "profile in use" and exits instantly (black
    # screen over VNC). Clear the stale singletons before launching (safe: nothing
    # else uses this profile in the one-shot login container).
    rm -f "$CHROMIUM_USER_DATA_DIR"/Singleton* 2>/dev/null || true
    launch_browser "${1:-https://linear.app}" full
    log "login: Chromium up on $DISPLAY_NUM with persistent profile $CHROMIUM_USER_DATA_DIR"
    # macOS Screen Sharing refuses password-less VNC, so honor VNC_PASSWORD when set
    # (one-time throwaway, never persisted). Falls back to -nopw for clients that allow it.
    if [ -n "${VNC_PASSWORD:-}" ]; then
      log "login: starting x11vnc on :5900 (password auth) — connect your VNC viewer and log into Linear, then Ctrl-C"
      exec x11vnc -display "$DISPLAY_NUM" -forever -shared -passwd "$VNC_PASSWORD" -rfbport 5900 -listen 0.0.0.0 -quiet
    fi
    log "login: starting x11vnc on :5900 (no auth) — connect your VNC viewer, log into Linear, then Ctrl-C"
    exec x11vnc -display "$DISPLAY_NUM" -forever -shared -nopw -rfbport 5900 -listen 0.0.0.0 -quiet
    ;;
  snapshot)        start_xvfb; snapshot "${1:-/recordings/frame.png}" ;;
  has-window)
    start_xvfb
    if has_mapped_window; then echo yes; exit 0; else echo no; exit 1; fi
    ;;
  *) echo "usage: entrypoint.sh {idle|surface-url URL|navigate URL|surface-html FILE|surface-memory FILE [where]|surface-split LOG HTML [TITLE]|surface-logterm LOG [TITLE]|surface-banner [MSG]|login [URL]|start [NAME]|stop|snapshot [OUT]|has-window}" >&2; exit 2 ;;
esac
