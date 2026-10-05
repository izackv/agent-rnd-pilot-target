#!/usr/bin/env bash
# Pull-based production deploy for CT 206 (control repo decision D-13).
# Runs from a systemd timer. Pulls the `:production` tag; if its digest changed (or the
# container is not running), restarts via docker compose and checks health. No inbound
# credential exists on this host: the only thing that can change production is the
# owner-approved `deploy` job in the release workflow, which moves the `:production` tag.
set -euo pipefail
IMAGE="${PILOT_TARGET_IMAGE:-ghcr.io/izackv/agent-rnd-pilot-target:production}"
DIR="${PILOT_TARGET_DIR:-/opt/pilot-target}"
cd "$DIR"
before=$(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE" 2>/dev/null || echo none)
docker pull -q "$IMAGE" >/dev/null
after=$(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE")
if [ "$before" != "$after" ] || ! docker ps --format '{{.Names}}' | grep -qx pilot-target; then
  PILOT_TARGET_IMAGE="$IMAGE" docker compose up -d --remove-orphans
  sleep 3
  curl -fsS http://127.0.0.1:8081/healthz >/dev/null
  logger -t pilot-target "deployed $after (was $before)"
  echo "deployed $after"
else
  echo "up to date ($after)"
fi
