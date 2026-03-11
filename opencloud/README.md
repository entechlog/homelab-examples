# OpenCloud – Self-Hosted File Hosting with Cloudflare Tunnel

Self-hosted [OpenCloud](https://opencloud.eu) file hosting on a home server, exposed securely via [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — no open inbound ports required.

---

## How it works

```
Internet
   │  HTTPS (TLS terminated by Cloudflare)
   ▼
Cloudflare Edge
   │  Encrypted tunnel (outbound only — no open ports on your server)
   ▼
cloudflared  (system service or Docker container on your home server)
   └─► http://<HOST_IP>:9200  →  OpenCloud
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Linux home server | Any distro, x86-64 or ARM64 |
| Docker + Compose v2 | [Install guide](https://docs.docker.com/engine/install/) |
| Cloudflare account | Free tier is sufficient |
| Domain on Cloudflare | You only need subdomains (e.g. `cloud.yourdomain.com`) |

---

## Setup

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set:

```dotenv
COMPOSE_FILE=docker-compose.yml:external-proxy/opencloud.yml
COMPOSE_PATH_SEPARATOR=:

PROXY_TLS=false
INSECURE=true

OC_DOMAIN=cloud.yourdomain.com
INITIAL_ADMIN_PASSWORD=YourStrongPasswordHere

# Linux: /mnt/external-drive/opencloud (must be owned by 1000:1000)
# Windows: D:/opencloud-data (use forward slashes)
OC_DATA_DIR=/mnt/external-drive/opencloud
OC_DEFAULT_QUOTA=53687091200
```

| Variable | Description |
|---|---|
| `HOST_IP` | Host LAN IP — required when `cloudflared` runs as a Docker container (e.g. `192.168.0.180`). Omit if `cloudflared` runs as a system service (defaults to `127.0.0.1`) |
| `OC_DOMAIN` | Your public domain (must match Cloudflare Tunnel route) |
| `INITIAL_ADMIN_PASSWORD` | Admin password — set before first start, cannot change via env after |
| `PROXY_TLS` | `false` for Cloudflare Tunnel, `true` for local testing |
| `OC_DATA_DIR` | Where user files are stored — point to your external drive. Linux: must be owned by `1000:1000` (`sudo chown -R 1000:1000 /path`). Windows: use forward slashes (e.g. `D:/opencloud-data`) |
| `OC_DEFAULT_QUOTA` | Per-user storage limit in bytes (50 GB = 53687091200, 0 = unlimited) |

### 2. Test locally

Before setting up Cloudflare, verify OpenCloud works on your server.

Set these two values in `.env`:

```dotenv
OC_DOMAIN=localhost:9200
PROXY_TLS=true
```

Start and open **https://localhost:9200** (accept the self-signed cert warning):

```bash
docker compose up -d
```

Log in with **admin** / your `INITIAL_ADMIN_PASSWORD`. Upload a file, create a folder — confirm it works.

### 3. Switch to production domain

Once local testing is confirmed, update `.env`:

```dotenv
OC_DOMAIN=cloud.yourdomain.com
PROXY_TLS=false
```

Restart clean (volumes must be recreated because the domain is baked into the config on first start):

```bash
docker compose down -v && docker compose up -d
```

### 4. Set up Cloudflare Tunnel

> **Important — `localhost` vs host IP:**
> If `cloudflared` runs as a **system service**, it shares the host network and can reach `localhost:9200`.
> If `cloudflared` runs as a **Docker container**, `localhost` inside the container refers to the container itself — not the host. You must use the host's LAN IP instead (e.g. `192.168.0.180:9200`). Set `HOST_IP` in `.env` so the port is bound to the correct interface.

#### Option A — Zero Trust dashboard (recommended for first time)

1. Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com) → **Networks → Tunnels**
2. Create a tunnel → choose **Cloudflared** → name it (e.g. `homelab`)
3. Copy the tunnel token
4. Install `cloudflared` on your server:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb
sudo cloudflared service install <YOUR_TUNNEL_TOKEN>
sudo systemctl enable --now cloudflared
```

5. Add a **Public Hostname** route in the dashboard:

| Subdomain | Domain | Type | URL |
|---|---|---|---|
| `cloud` | `yourdomain.com` | HTTP | `http://<HOST_IP>:9200` |

Replace `<HOST_IP>` with `localhost` (system service) or your server's LAN IP (Docker container).

#### Option B — Config file (reproducible / GitOps)

Create `/etc/cloudflared/config.yml`:

```yaml
tunnel: <YOUR_TUNNEL_ID>
credentials-file: /etc/cloudflared/<YOUR_TUNNEL_ID>.json

ingress:
  - hostname: cloud.yourdomain.com
    service: http://<HOST_IP>:9200    # localhost (system service) or LAN IP (Docker)
  - service: http_status:404
```

```bash
sudo systemctl enable --now cloudflared
```

### 5. Verify

Open `https://cloud.yourdomain.com` in your browser.

- **Username:** `admin`
- **Password:** the value you set for `INITIAL_ADMIN_PASSWORD`

---

## Storage limits

| Limit | How it's enforced |
|---|---|
| **Per user** | `OC_DEFAULT_QUOTA` in `.env` (default: 50 GB) |
| **Total service** | Size of the partition/drive mounted at `OC_DATA_DIR` — use a partition or host filesystem quota to cap (e.g. 250 GB) |

---

## Updating

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

To pin a specific version, set `OC_DOCKER_TAG=x.y.z` in `.env`.

---

## Useful commands

```bash
docker compose logs -f              # View logs
docker compose down                 # Stop (safe — all data preserved)
docker compose up -d                # Start (picks up where it left off)
docker compose exec opencloud sh    # Shell into the container
sudo systemctl status cloudflared   # Check tunnel status (Linux system service)
```

### Full reset (destroy all data and reinitialize)

Use this only when you want to start completely fresh (e.g. changing `OC_DOMAIN`).

> **Warning:** Never use `docker compose down -v` by itself. The `-v` flag deletes the config volume (which holds internal system passwords) but leaves `OC_DATA_DIR` intact (it's a bind mount). This mismatch causes `LDAP Invalid Credentials` errors on the next start. Always clean both together:

```bash
# Linux
docker compose down -v
rm -rf /path/to/your/OC_DATA_DIR/*
docker compose up -d

# Windows (PowerShell)
docker compose down -v
Remove-Item -Path "C:\path\to\your\OC_DATA_DIR\*" -Recurse -Force
docker compose up -d
```

---

## References

- [OpenCloud documentation](https://docs.opencloud.eu)
- [OpenCloud compose repository](https://github.com/opencloud-eu/opencloud-compose)
- [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
