# Pocket ID – Lightweight OIDC Provider with Cloudflare Tunnel

Self-hosted [Pocket ID](https://pocket-id.org) as a centralized OIDC identity provider for homelab SSO, exposed securely via [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) — no open inbound ports required.

Pocket ID uses passkey-based authentication (no passwords to manage) and provides a web UI for managing OIDC clients.

---

## How it works

```
Internet
   |  HTTPS (TLS terminated by Cloudflare)
   v
Cloudflare Edge
   |  Encrypted tunnel (outbound only — no open ports on your server)
   v
cloudflared  (system service or Docker container on your home server)
   +-- http://<HOST_IP>:1411  -->  Pocket ID (OIDC provider + admin UI)
                                     |
                                     |  OIDC (authorization_code + refresh_token)
                                     v
                                  OpenCloud, Immich, etc.
```

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Linux home server | Any distro, x86-64 or ARM64 |
| Docker + Compose v2 | [Install guide](https://docs.docker.com/engine/install/) |
| Cloudflare account | Free tier is sufficient |
| Domain on Cloudflare | You only need a subdomain (e.g. `pocket-id.yourdomain.com`) |

---

## Setup

### 1. Configure environment

```bash
cp .env.example .env
```

Generate the encryption key — either use the script or do it manually:

```bash
# Option A: Script (generates key and writes it into .env)
chmod +x scripts/generate-encryption-key.sh
./scripts/generate-encryption-key.sh

# Option B: Manual
openssl rand -base64 32
# Then paste the output into .env as ENCRYPTION_KEY=<value>
```

Edit `.env` — the only values you **must** set:

```dotenv
APP_URL=https://pocket-id.yourdomain.com
ENCRYPTION_KEY=<generated key>
```

All other variables have sensible defaults. Uncomment and change them only if needed:

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_URL` | Yes | — | Public HTTPS URL for Pocket ID (must be HTTPS — passkeys require secure context) |
| `ENCRYPTION_KEY` | Yes | — | Data encryption key. Generate with `openssl rand -base64 32` or the script |
| `HOST_IP` | Only if cloudflared is a Docker container | `127.0.0.1` | Host LAN IP so cloudflared can reach Pocket ID |
| `TRUST_PROXY` | No | `false` | Set `true` when behind Cloudflare Tunnel |
| `ALLOW_USER_SIGNUPS` | No | `disabled` | `disabled` = admin creates users, `withToken` = invite-only, `open` = anyone can sign up |
| `PUID` / `PGID` | No | `1000` | Container user/group IDs |
| `POCKET_ID_DATA_DIR` | No | `./data` | Where SQLite DB and uploads are stored |

### 2. Set up Cloudflare Tunnel

Add a **Public Hostname** route in the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com) (Networks > Tunnels) **before** first start, since passkeys require HTTPS:

| Subdomain | Domain | Type | URL |
|---|---|---|---|
| `pocket-id` | `yourdomain.com` | HTTP | `http://<HOST_IP>:1411` |

> **Important — `localhost` vs host IP:**
> If `cloudflared` runs as a **system service**, use `localhost:1411`.
> If `cloudflared` runs as a **Docker container**, use the host's LAN IP (e.g. `192.168.0.180:1411`). Set `HOST_IP` in `.env`.

### 3. Start Pocket ID

```bash
docker compose up -d
```

### 4. Create admin account

Open `https://pocket-id.yourdomain.com/setup` in your browser. Register your first passkey — this becomes the admin account.

### 5. Create OIDC client for OpenCloud

1. In the Pocket ID admin UI, go to **OIDC Clients** and create a new client
2. Set the **name** to `OpenCloud`
3. Set **Client Launch URL** to `https://cloud.yourdomain.com`
4. Add **callback URL**: `https://cloud.yourdomain.com/oidc-callback.html`
5. Add **logout callback URL**: `https://cloud.yourdomain.com`
6. Check **Public** (OpenCloud's web client does not use a client secret)
7. Leave **PKCE** enabled
8. Save — copy the generated **Client ID**

### 6. Configure OpenCloud

Add these environment variables to your OpenCloud `.env`:

```dotenv
OC_OIDC_ISSUER=https://pocket-id.yourdomain.com
OC_EXCLUDE_RUN_SERVICES=idp
WEB_OIDC_CLIENT_ID=<client-id-from-pocket-id>
PROXY_OIDC_REWRITE_WELLKNOWN=true
PROXY_USER_OIDC_CLAIM=preferred_username
PROXY_USER_CS3_CLAIM=username
PROXY_AUTOPROVISION_ACCOUNTS=true
PROXY_OIDC_ACCESS_TOKEN_VERIFY_METHOD=none
WEB_OIDC_SCOPE=openid profile email groups
WEB_OIDC_POST_LOGOUT_REDIRECT_URI=https://cloud.yourdomain.com
PROXY_ROLE_ASSIGNMENT_DRIVER=oidc
GRAPH_ASSIGN_DEFAULT_USER_ROLE=true
IDP_DOMAIN=pocket-id.yourdomain.com
```

| Variable | Description |
|---|---|
| `OC_OIDC_ISSUER` | Pocket ID URL — OpenCloud uses this for OIDC discovery |
| `OC_EXCLUDE_RUN_SERVICES` | Disables OpenCloud's built-in identity provider (Pocket ID replaces it) |
| `WEB_OIDC_CLIENT_ID` | Client ID from Pocket ID |
| `PROXY_AUTOPROVISION_ACCOUNTS` | Automatically creates OpenCloud accounts on first OIDC login |
| `WEB_OIDC_SCOPE` | Must include `groups` for role mapping to work |
| `WEB_OIDC_POST_LOGOUT_REDIRECT_URI` | Redirects back to OpenCloud login page after OIDC logout |
| `PROXY_ROLE_ASSIGNMENT_DRIVER` | Set to `oidc` to assign roles based on Pocket ID group claims |
| `IDP_DOMAIN` | Pocket ID domain — required for Content Security Policy (allows browser redirects) |

Do a full reset of OpenCloud after adding these variables (the OIDC issuer is baked into OpenCloud's config on first start):

```bash
cd ../opencloud
docker compose down -v
rm -rf /path/to/your/OC_DATA_DIR/*
docker compose up -d
```

> **Warning:** You must clean both the config volume (`-v`) and `OC_DATA_DIR` together. Cleaning only one causes `LDAP Invalid Credentials` errors. See the [OpenCloud README](../opencloud/README.md#full-reset-destroy-all-data-and-reinitialize) for details.

See the [OpenCloud + Pocket ID integration guide](https://github.com/orgs/opencloud-eu/discussions/1018) for full details including desktop and mobile clients.

### 7. Verify

1. Open `https://pocket-id.yourdomain.com` — Pocket ID login page loads
2. Open `https://cloud.yourdomain.com` — redirects to Pocket ID for login
3. Authenticate with passkey — redirects back to OpenCloud
4. Log out from OpenCloud — redirects back to OpenCloud login page (not stuck on Pocket ID)

---

## User management

### Invite-only signup

Set `ALLOW_USER_SIGNUPS=withToken` in `.env` to restrict registration to invite links only:

1. In the Pocket ID admin UI, go to **Settings > Admin > Users**
2. Click **Create Signup Token** — generates a one-time invite link
3. Send the link to the person you want to invite
4. They register their passkey using the link — no one else can use it

### Role mapping with OpenCloud

Pocket ID user groups can be mapped to OpenCloud roles (admin, user, etc.). OpenCloud reads group names from the OIDC `groups` claim.

1. In Pocket ID, go to **Settings > Admin > User Groups** and create groups (e.g. `opencloud-admins`, `opencloud-users`)
2. Assign users to the appropriate groups
3. In OpenCloud, edit `config/opencloud/proxy.yaml` to map group names to roles:

```yaml
role_assignment:
  driver: oidc
  oidc_role_mapper:
    role_claim: groups
    role_mapping:
      - role_name: admin
        claim_value: opencloud_admins    # Pocket ID group slug (lowercase, underscores)
      - role_name: user
        claim_value: opencloud_users
```

> **Note:** Pocket ID uses the group **slug** (lowercase, underscores) in OIDC claims, not the display name. Check the slug in the Pocket ID admin UI.

---

## Adding more OIDC clients

In the Pocket ID admin UI:

1. Go to **OIDC Clients** > **Add Client**
2. Set the name, callback URL(s), and scopes
3. Copy the generated Client ID and Client Secret to the target service

No config files to edit, no restarts needed.

---

## Updating

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

---

## Useful commands

```bash
docker compose logs -f              # View logs
docker compose down                 # Stop (safe — all data preserved)
docker compose up -d                # Start
docker compose exec pocket-id sh    # Shell into the container
```

### Full reset

```bash
docker compose down
rm -rf data/*                       # Or $POCKET_ID_DATA_DIR/* if customized
docker compose up -d
# Then visit https://pocket-id.yourdomain.com/setup to re-register admin
```

---

## References

- [Pocket ID documentation](https://pocket-id.org/docs/setup/installation)
- [Pocket ID environment variables](https://pocket-id.org/docs/configuration/environment-variables)
- [OpenCloud + Pocket ID integration](https://github.com/orgs/opencloud-eu/discussions/1018)
- [Cloudflare Tunnel documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
