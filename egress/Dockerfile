# Deny-by-default egress CONNECT proxy (Phase 2 / P1).
#
# The runtime enforcement point for the sovereign-egress allow-list. Wraps the
# stdlib-only egress_proxy.py in a minimal Python image; the reviewable
# egress/policy.yaml is mounted READ-ONLY at /etc/egress/policy.yaml by
# docker-compose (service `egress-proxy`, profile `egress`). The proxy refuses any
# HTTP CONNECT whose host:port is not declared `enforce` in that policy.
#
# stdlib-only by design (no PyYAML, no third-party deps) so a clean clone builds
# it with nothing to install — matching the repo's reference-client convention.
FROM python:3.12-slim

ENV EGRESS_POLICY=/etc/egress/policy.yaml \
    EGRESS_PORT=8888

WORKDIR /opt/egress
COPY egress_proxy.py /opt/egress/egress_proxy.py

EXPOSE 8888

# Healthcheck: the listener is accepting connections on EGRESS_PORT.
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import socket,os,sys; s=socket.socket(); s.settimeout(3); sys.exit(0 if s.connect_ex(('127.0.0.1', int(os.environ.get('EGRESS_PORT','8888'))))==0 else 1)" || exit 1

ENTRYPOINT ["python", "/opt/egress/egress_proxy.py"]
