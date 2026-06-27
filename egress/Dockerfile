# Confinable OpenShell sandbox base image (Phase 2 / P1).
#
# This is NOT a proxy. It is the base image OpenShell builds and runs the egress
# gate's probe inside, via:
#
#   openshell sandbox create --no-keep --policy egress/policy.yaml \
#     --from egress/ -- sh -c '<curl probes>'
#
# OpenShell's supervisor becomes PID 1, auto-injects HTTPS_PROXY, and enforces the
# network allow-list in egress/policy.yaml against every outbound CONNECT.
#
# The image MUST contain:
#   - iproute2 (the `ip` binary) — required by the OpenShell supervisor to set up
#     the sandbox network namespace.
#   - a `sandbox` user/group — the policy's process.run_as_user/run_as_group.
#   - curl + ca-certificates — the gate's CONNECT probe (negative + positive).
#
# Verified building + confining successfully under OpenShell 0.0.71 on Docker
# Engine 28.1.1 (Docker Desktop 4.41.2) / Apple Silicon.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates iproute2 \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -r sandbox && useradd -r -g sandbox -m -d /sandbox sandbox
