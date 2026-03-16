# homelab-examples

Docker Compose setups and configurations for self-hosted homelab services.

## Services

| Service | Description | Directory |
|---|---|---|
| [Home Assistant](https://www.home-assistant.io/) | Smart home automation — dashboards, themes, and configurations | [`home-assistant/`](home-assistant/) |
| [Immich](https://immich.app/) | Self-hosted photo & video management with external library support | [`immich/`](immich/) |
| [OpenCloud](https://opencloud.eu) | Self-hosted file hosting (like ownCloud/Nextcloud) | [`opencloud/`](opencloud/) |
| [Pocket ID](https://pocket-id.org) | Lightweight OIDC identity provider with passkey auth | [`pocket-id/`](pocket-id/) |

## Architecture

```
Internet
   |  HTTPS (TLS terminated by Cloudflare)
   v
Cloudflare Edge
   |  Encrypted tunnel (outbound only)
   v
cloudflared (on your home server)
   +-- http://<HOST_IP>:9200  -->  OpenCloud (file hosting)
   +-- http://<HOST_IP>:1411  -->  Pocket ID  (OIDC / SSO)
```

## Quick start

Each service has its own README with full setup instructions.

1. **[OpenCloud](opencloud/README.md)** — set up file hosting first (works standalone with its built-in identity provider)
2. **[Pocket ID](pocket-id/README.md)** — optionally add centralized SSO with passkey authentication

Pocket ID is an optional enhancement — users authenticate once with a passkey and get access to all connected services.

## Common patterns

- Each service uses a base `docker-compose.yml` + an `external-proxy/*.yml` overlay for port binding
- Configuration via `.env` files (`.env.example` provided as templates, `.env` is gitignored)
- All services are designed to work behind Cloudflare Tunnel with `PROXY_TLS=false`
- `HOST_IP` controls which interface the port binds to (set to LAN IP when cloudflared runs as Docker container)
