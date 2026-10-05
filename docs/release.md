# Release flow

1. An integrated commit on `main` is chosen; the `release` workflow is dispatched with its SHA.
2. `build` refuses any SHA not on `main`, builds the image and pushes `ghcr.io/izackv/agent-rnd-pilot-target:<sha>`.
3. `deploy` waits for the owner's approval in the `production` environment (the human gate).
4. On approval it promotes that exact image to the `:production` tag. Nothing logs into 206.
5. CT 206 runs a systemd timer (`deploy/ct206/`) that pulls `:production` every two minutes and
   restarts the container when the digest changes, then checks `/healthz`.

Rollback: re-run the workflow with the previous SHA and approve; the poller moves back.
