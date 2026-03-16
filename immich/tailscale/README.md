# Tailscale for Immich

Remote access to Immich via a Tailscale Docker sidecar with automatic HTTPS. Access Immich at `https://immich.<tailnet-name>.ts.net` without opening any ports.

## Prerequisites

1. A [Tailscale account](https://tailscale.com/)
2. Immich running via the `windows/docker-compose.yml` setup
3. In the [Tailscale admin console](https://login.tailscale.com/admin):
   - Enable **MagicDNS** under [DNS settings](https://login.tailscale.com/admin/dns)
   - Enable **HTTPS Certificates** under [DNS settings](https://login.tailscale.com/admin/dns)
   - Generate an **auth key** under [Settings > Keys](https://login.tailscale.com/admin/settings/keys)

## Setup

```bash
cp .env.template .env
```

Edit `.env` with your values:
- `TS_AUTHKEY` - your Tailscale auth key
- `IMMICH_HOST` - IP address of your machine running Immich (e.g., `192.168.0.180`)

## Start

```bash
docker compose up -d
```

## Sharing with Family

Family members need to:
1. Get invited to your tailnet - go to [Users](https://login.tailscale.com/admin/users) in admin console and invite them
2. Install the Tailscale app on their device ([iOS](https://apps.apple.com/app/tailscale/id1470499037), [Android](https://play.google.com/store/apps/details?id=com.tailscale.ipn), desktop)
3. Sign in with their invited account
4. Access `https://immich.<tailnet-name>.ts.net`

The Tailscale container must be running on your machine for remote access to work. With `restart: unless-stopped`, it starts automatically with Docker Desktop.

## Troubleshooting

### Container not joining tailnet
Verify your auth key is valid. Check logs: `docker logs immich_tailscale`

### Name shows as immich-2, immich-3, etc.
Old nodes still exist in your tailnet. Remove them from [Machines](https://login.tailscale.com/admin/machines), then recreate:
```bash
docker compose down -v && docker compose up -d
```
Only use `-v` when you need to reset the node identity. Normal restarts should use `docker compose down && docker compose up -d`.

## References

- [Tailscale Docker Guide](https://tailscale.com/blog/docker-tailscale-guide)
- [Immich Remote Access](https://docs.immich.app/guides/remote-access/)
- [Tailscale ACL Tags](https://tailscale.com/kb/1068/acl-tags)
