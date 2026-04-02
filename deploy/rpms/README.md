# Local RPM drop zone (RHEL 9)

Place **offline** `dnf`-compatible RPMs here (e.g. `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-compose-plugin`, dependencies) and run:

```bash
sudo RPM_DIR="$(pwd)" ../bootstrap/install-docker-rhel9-offline.sh
```

Exact filenames depend on your vendor mirror and minor RHEL release—this repo cannot ship them.
