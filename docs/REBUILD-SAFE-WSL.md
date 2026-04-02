# Safe rebuild (WSL, low space on C:)

Your repo lives on **E:** (`/mnt/e/loomin-docs`). Image build cache inside WSL may still use the **WSL virtual disk** (often on **C:**). To run updates safely:

## 1. Work only from E:

```bash
cd /mnt/e/loomin-docs
```

Do **not** clone or `docker build` from `C:\Users\...` unless you must.

## 2. Rebuild only what changed (saves time and disk)

After UI or nginx changes:

```bash
sudo docker-compose build frontend
sudo docker-compose up -d frontend
```

After backend changes:

```bash
sudo docker-compose build backend
sudo docker-compose up -d backend
```

Full stack (if compose file or bases changed):

```bash
sudo docker-compose build
sudo docker-compose up -d
```

## 3. Trim Docker when finished testing (optional)

**Warning:** removes unused images/containers; review before running.

```bash
sudo docker system prune -f
```

To also remove unused volumes (deletes **named volume data** like `loomin_data` if container gone):

```bash
sudo docker volume ls
# only if you mean it:
# sudo docker system prune -af --volumes
```

## 4. Free WSL / C: further (optional)

- Uninstall **Docker Desktop** if you only use **Docker inside Ubuntu**.
- In Windows: *Settings → System → Storage → Temporary files*.
- Move **WSL** ext4 VHD to another drive (Microsoft docs: export/import distro).

## 5. Verify after rebuild

```bash
curl -s http://127.0.0.1/health
curl -s http://127.0.0.1:8000/health
```

Open **http://localhost/** — status strip should show **API reachable**.
