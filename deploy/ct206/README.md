# Production on CT 206 (pull-based)

One-time install, as root on CT 206 (the host only needs outbound HTTPS to ghcr.io):

```
mkdir -p /opt/pilot-target && cd /opt/pilot-target
curl -fsSLO https://raw.githubusercontent.com/izackv/agent-rnd-pilot-target/main/compose.yaml
for f in pilot-target-pull.sh pilot-target-pull.service pilot-target-pull.timer; do
  curl -fsSLO https://raw.githubusercontent.com/izackv/agent-rnd-pilot-target/main/deploy/ct206/$f
done
chmod +x pilot-target-pull.sh
cp pilot-target-pull.service pilot-target-pull.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now pilot-target-pull.timer
./pilot-target-pull.sh          # first deploy now; afterwards the timer polls every 2 min
curl -fsS http://127.0.0.1:8081/healthz
```

The GHCR package `agent-rnd-pilot-target` must be **public** for an anonymous pull (it is a
toy app). Otherwise run `docker login ghcr.io` on 206 once with a read-only token.

Flow: release workflow → owner approves the `production` environment → `deploy` job retags
the approved image as `:production` → this timer notices the new digest and restarts.
