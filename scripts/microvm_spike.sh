#!/usr/bin/env bash
#
# microvm_spike.sh — GLO-14 P4 host-orchestrator MicroVM confinement SPIKE (Q9 Option A).
#
# WHAT THIS IS. A *spike*, not a production build. The host Hermes orchestrator runs
# OUTSIDE any sandbox today; the GLO-13 P1 egress slice only confines the *containerized*
# sub-tools. Confining the host orchestrator itself means moving it into a MicroVM
# (OpenShell's `vm` compute driver: libkrun + Apple Hypervisor.framework). That is the
# biggest moving-parts/DNS risk in the stack, so design Q9 resolved to **spike + document**
# (Option A) rather than commit a fragile default build. The DELIVERABLE of this script is
# the scripted ATTEMPT + the captured EVIDENCE (a timestamped log) + the documented
# tradeoffs/go-no-go in docs/system-design-tradeoffs.md — NOT a booted VM.
#
# WHAT IT DOES, graceful-degradation-first (it must ALWAYS exit 0 and ALWAYS leave a
# usable log; it never requires sudo and never destructively reconfigures the running
# gateway the egress gate depends on):
#   1. record host facts (arch, openshell version, Docker, the active compute driver);
#   2. locate the opt-in `vm` compute-driver binary (openshell-driver-vm) and check it
#      carries the com.apple.security.hypervisor entitlement;
#   3. ATTEMPT to launch the vm driver to a private gRPC socket far enough to prove it
#      boots on THIS Apple-Silicon host (it binds Hypervisor.framework), capturing how far
#      it got — this is the "did the vm driver exist / boot?" evidence;
#   4. note the remaining steps the spike deliberately stops short of (a full gateway
#      `OPENSHELL_DRIVERS=vm` reconfigure + bootstrap image + guest-TLS + running the host
#      orchestrator inside the guest), because those are the fragile parts Q9 defers;
#   5. attempt `openshell status` for the gateway/driver picture;
#   6. write EVERYTHING to recordings/microvm_spike_<ts>.log and print its path.
#
# Inference stays CLOUD (Nous Portal) throughout — there is no CUDA on Apple Silicon, so a
# local-GPU guest is out of scope (one of the four documented macOS limitations).
#
# The companion gate scripts/assert_microvm_spike.py reads the log + asserts the dated
# go/no-go section exists, and — WHEN the VM reached boot — runs the deterministic per-bug
# probes (.local mDNS non-traversal, Landlock best_effort no-op, virtio-fs case-sensitivity)
# and asserts each behaves as documented; each probe self-skips if the VM didn't get far
# enough, so the gate degrades gracefully too.
#
# Usage:
#   bash scripts/microvm_spike.sh
#   MICROVM_SPIKE_BOOT_SECONDS=12 bash scripts/microvm_spike.sh   # widen the boot window
#
# Exit code: ALWAYS 0 (a spike that can't boot the VM on this host is an EXPECTED, recorded
# outcome — the evidence is the deliverable). Genuine harness mistakes still print to stderr.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$REPO_ROOT/recordings"
LOG="$LOG_DIR/microvm_spike_${TS}.log"
mkdir -p "$LOG_DIR"

# How long to let the vm driver attempt to come up before we tear it down. Short by
# default — we only need to observe whether it BINDS/BOOTS, not run a workload.
BOOT_SECONDS="${MICROVM_SPIKE_BOOT_SECONDS:-10}"

# The opt-in vm compute-driver binary ships in OpenShell's libexec; it is NOT the default
# driver (the gateway auto-detects Docker). Search the conventional locations.
VM_DRIVER_CANDIDATES=(
  "/opt/homebrew/opt/openshell/libexec/openshell-driver-vm"
  "/usr/local/opt/openshell/libexec/openshell-driver-vm"
  "$HOME/.local/libexec/openshell/openshell-driver-vm"
  "/usr/local/libexec/openshell/openshell-driver-vm"
  "/usr/libexec/openshell/openshell-driver-vm"
)

# A non-symlinked state dir (the driver refuses a symlinked socket dir such as /tmp).
SPIKE_STATE="$HOME/.local/state/openshell-microvm-spike-${TS}"

# --- logging helper: everything goes to the log AND to the console -------------------
log() { printf '%s\n' "$*" | tee -a "$LOG"; }
hr()  { log "------------------------------------------------------------------------"; }

# These markers are what assert_microvm_spike.py greps for to decide which per-bug probes
# are in scope. Keep them stable.
#   VM_DRIVER_PRESENT=yes|no   — the opt-in binary exists
#   VM_DRIVER_BOOTED=yes|no    — it bound its gRPC socket (the VM layer came up)
VM_DRIVER_PRESENT="no"
VM_DRIVER_BOOTED="no"

{
  log "=== GLO-14 P4 — host-orchestrator MicroVM confinement SPIKE (Q9 Option A) ==="
  log "timestamp:        ${TS}"
  log "repo:             ${REPO_ROOT}"
  log "note:             this is a SPIKE — the deliverable is this evidence + the dated"
  log "                  go/no-go in docs/system-design-tradeoffs.md, NOT a booted VM."
  log "inference:        CLOUD (Nous Portal) — no CUDA on Apple Silicon; no local-GPU guest."
  hr

  # --- 1. host facts ------------------------------------------------------------------
  log "[1] host facts"
  log "    uname:          $(uname -msr 2>&1)"
  log "    arch:           $(uname -m 2>&1)"
  if command -v sw_vers >/dev/null 2>&1; then
    log "    macOS:          $(sw_vers -productVersion 2>&1) (build $(sw_vers -buildVersion 2>&1))"
  fi
  if command -v openshell >/dev/null 2>&1; then
    log "    openshell:      $(openshell --version 2>&1 | head -1)"
  else
    log "    openshell:      NOT FOUND on PATH — the vm driver ships with OpenShell"
  fi
  if command -v docker >/dev/null 2>&1; then
    log "    docker:         $(docker --version 2>&1 | head -1)"
    if docker info >/dev/null 2>&1; then
      log "    docker daemon:  running (the DEFAULT, auto-detected compute driver)"
    else
      log "    docker daemon:  not reachable"
    fi
  else
    log "    docker:         NOT FOUND on PATH"
  fi
  hr

  # --- 2. locate the opt-in vm driver binary + entitlement ----------------------------
  log "[2] opt-in 'vm' compute driver (libkrun + Hypervisor.framework)"
  log "    NOTE: the gateway auto-detects Docker; the vm driver is OPT-IN ONLY"
  log "          (set OPENSHELL_DRIVERS=vm / a gateway.toml [openshell.drivers.vm] table)."
  VM_DRIVER=""
  for cand in "${VM_DRIVER_CANDIDATES[@]}"; do
    if [ -x "$cand" ]; then
      VM_DRIVER="$cand"
      break
    fi
  done
  if [ -n "$VM_DRIVER" ]; then
    VM_DRIVER_PRESENT="yes"
    log "    vm driver:      FOUND at ${VM_DRIVER}"
    if command -v codesign >/dev/null 2>&1; then
      if codesign -d --entitlements - "$VM_DRIVER" 2>&1 | grep -q "com.apple.security.hypervisor"; then
        log "    entitlement:    com.apple.security.hypervisor PRESENT"
        log "                    (the binary is allowed to use Apple Hypervisor.framework)"
      else
        log "    entitlement:    com.apple.security.hypervisor MISSING"
        log "                    (libkrun would be denied the hypervisor — a known macOS"
        log "                     packaging hazard; the gateway could not boot a guest)"
      fi
    fi
  else
    log "    vm driver:      NOT FOUND in any conventional libexec path:"
    for cand in "${VM_DRIVER_CANDIDATES[@]}"; do log "                      ${cand}"; done
    log "                    => the vm driver is not installed on this host; the spike"
    log "                       cannot reach a MicroVM boot. This is an EXPECTED spike"
    log "                       outcome (Q9: the deliverable is the attempt + the doc)."
  fi
  log "VM_DRIVER_PRESENT=${VM_DRIVER_PRESENT}"
  hr

  # --- 3. attempt to BOOT the vm driver far enough to bind its gRPC socket ------------
  log "[3] attempt: launch the vm driver far enough to prove it boots on this host"
  if [ "$VM_DRIVER_PRESENT" = "yes" ]; then
    rm -rf "$SPIKE_STATE" 2>/dev/null || true
    mkdir -p "$SPIKE_STATE" 2>/dev/null || true
    SOCK="$SPIKE_STATE/driver.sock"
    log "    state-dir:      ${SPIKE_STATE}"
    log "    socket:         ${SOCK}"
    log "    launching:      ${VM_DRIVER} (${BOOT_SECONDS}s window) ..."
    # Launch in the background, give it a moment to bind, then observe + tear down. We do
    # NOT touch the running gateway — this is a STANDALONE driver process to a private
    # socket. --openshell-endpoint points at the conventional gateway gRPC port so the
    # driver has somewhere to register; we only need to observe whether the VM layer
    # (libkrun/Hypervisor.framework) comes up enough to bind the socket.
    set +e
    OPENSHELL_LOG_LEVEL=debug \
      "$VM_DRIVER" \
        --bind-socket "$SOCK" \
        --allow-same-uid-peer \
        --openshell-endpoint "http://127.0.0.1:50051" \
        --state-dir "$SPIKE_STATE/state" \
        >>"$LOG" 2>&1 &
    DRIVER_PID=$!
    set -e 2>/dev/null || true

    # Poll for the socket up to BOOT_SECONDS.
    bound="no"
    for _ in $(seq 1 "$((BOOT_SECONDS * 2))"); do
      if [ -S "$SOCK" ]; then bound="yes"; break; fi
      if ! kill -0 "$DRIVER_PID" 2>/dev/null; then break; fi
      sleep 0.5
    done

    if [ "$bound" = "yes" ]; then
      VM_DRIVER_BOOTED="yes"
      log ""
      log "    result:         the vm compute driver BOUND its gRPC socket"
      log "                    => libkrun acquired Hypervisor.framework and the VM layer"
      log "                       came up on this Apple-Silicon host."
      log "                    The state dir was created with images/ + sandboxes/:"
      ls -la "$SPIKE_STATE/state" 2>&1 | sed 's/^/                      /' | tee -a "$LOG" >/dev/null
    else
      log ""
      log "    result:         the vm compute driver did NOT bind its socket within"
      log "                    ${BOOT_SECONDS}s (it exited or never came up). See the driver"
      log "                    output above for the reason. This is a recorded spike"
      log "                    outcome — the VM layer did not reach boot on this host."
    fi

    # Tear the standalone driver down (never leave it running; never touch the gateway).
    kill "$DRIVER_PID" 2>/dev/null || true
    wait "$DRIVER_PID" 2>/dev/null || true
    rm -rf "$SPIKE_STATE" 2>/dev/null || true
  else
    log "    SKIP — vm driver binary absent; nothing to launch."
  fi
  log "VM_DRIVER_BOOTED=${VM_DRIVER_BOOTED}"
  hr

  # --- 4. what the spike deliberately stops short of (Q9 Option A boundary) -----------
  log "[4] deliberately NOT attempted (the fragile parts Q9 defers to a later epic):"
  log "    - reconfiguring the RUNNING gateway to OPENSHELL_DRIVERS=vm (the egress gate"
  log "      depends on the Docker driver staying up — a destructive reconfigure is"
  log "      out of scope for a non-sudo spike);"
  log "    - building/pulling a guest bootstrap image + minting guest TLS materials;"
  log "    - running the host Hermes orchestrator INSIDE the guest and proving its egress"
  log "      is confined end-to-end."
  log "    These are exactly the moving parts that carry the four documented macOS"
  log "    limitations below; the spike's job is to surface them, not to ship them."
  hr

  # --- 5. gateway / driver status -----------------------------------------------------
  log "[5] openshell status (gateway + active driver picture)"
  if command -v openshell >/dev/null 2>&1; then
    openshell status 2>&1 | sed 's/^/    /' | tee -a "$LOG" >/dev/null || \
      log "    (openshell status returned non-zero — gateway may be down)"
  else
    log "    SKIP — openshell not on PATH."
  fi
  hr

  # --- 6. the four documented macOS limitations (recorded here + in the tradeoffs doc) -
  log "[6] the FOUR documented macOS limitations a MicroVM host-confinement build hits:"
  log "    (1) Landlock best_effort is a NO-OP on XNU — Landlock is a Linux LSM; on the"
  log "        macOS host kernel it silently degrades (OpenShell #803). Filesystem"
  log "        confinement is therefore NOT load-bearing here; the network OPA-CONNECT"
  log "        layer is."
  log "    (2) mDNS '.local' non-traversal — a guest cannot resolve host .local mDNS"
  log "        names (e.g. inference.local), so guest->host local-Ollama DNS is broken."
  log "        Inference stays CLOUD (Nous Portal), sidestepping the path entirely."
  log "    (3) No CUDA on Apple Silicon — no local GPU passthrough for inference; the"
  log "        --gpu vm-driver path is moot here. Inference is cloud, by design."
  log "    (4) Case-sensitive vs case-insensitive APFS over virtio-fs — the macOS host"
  log "        FS is case-INSENSITIVE by default while the Linux guest expects"
  log "        case-SENSITIVE; shared virtio-fs mounts can collide/resolve surprisingly."
  hr

  log "=== spike complete — evidence captured ==="
  log "    VM_DRIVER_PRESENT=${VM_DRIVER_PRESENT}"
  log "    VM_DRIVER_BOOTED=${VM_DRIVER_BOOTED}"
  log "    log: ${LOG}"
  log "    The go/no-go judgment is recorded in docs/system-design-tradeoffs.md"
  log "    (GLO-14 P4 section). assert_microvm_spike.py gates this evidence + that doc."
} 2>&1

# Surface the log path on stdout for callers/the gate (last line, parseable).
echo "SPIKE_LOG=${LOG}"
exit 0
