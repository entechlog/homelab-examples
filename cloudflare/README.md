# Cloudflare Tunnel for Immich

Public access to Immich via a Cloudflare Tunnel. Share photo albums with friends and family at `https://photos.yourdomain.com` — no VPN required, no port forwarding, free tier with built-in DDoS protection.

> **Upload limit:** Cloudflare free tier caps uploads at 100MB per request. This only affects uploading *through the tunnel* (large videos). Viewing shared albums is unaffected. For your own phone uploads, continue using Tailscale or local network which has no limit.

## Prerequisites

1. A domain managed by [Cloudflare](https://dash.cloudflare.com/) (free plan works)
2. Immich running via the `windows/docker-compose.yml` setup

## Cloudflare Dashboard Setup

1. Log in to [Cloudflare dashboard](https://dash.cloudflare.com/) → select your domain
2. Go to **Zero Trust** (left sidebar) → **Networks** → **Tunnels**
3. Click **Create a tunnel** → select **Cloudflared** → name it (e.g. `immich`)
4. Copy the tunnel token
5. Skip the connector install (we'll use Docker)
6. Add a public hostname:
   - **Subdomain:** `photos` (or your choice)
   - **Domain:** select your domain
   - **Service Type:** `HTTP`
   - **URL:** `192.168.0.180:2283` (your Immich host:port)
7. Save the tunnel

## Local Setup

```bash
cp .env.template .env
```

Edit `.env` and paste your tunnel token:
- `TUNNEL_TOKEN` — the token from step 4 above

Start the container:

```bash
docker compose up -d
```

Check logs to verify the tunnel connects:

```bash
docker logs immich_cloudflare
```

You should see `Connection registered` in the output. Browse to `https://photos.yourdomain.com` to confirm.

## Immich Configuration

For share links to use your custom domain instead of the internal IP:

1. Open Immich → **Administration** → **Settings** → **Server**
2. Set **External URL** to `https://photos.yourdomain.com`
3. Save

Now any share links you create will use the public domain.

## Security Tips

- **WAF rules** — enable in Cloudflare dashboard for bot protection
- **Cloudflare Access** — add email-based verification under Zero Trust → Access → Applications for an extra login layer
- **Share link settings** — set expiration dates and passwords on Immich share links
- **Firewall** — no ports need to be opened; `cloudflared` makes outbound-only connections

## Troubleshooting

### Tunnel not connecting
Verify your token is correct. Check logs: `docker logs immich_cloudflare`

### Share links still show internal IP
Set the External URL in Immich admin settings (see Immich Configuration above).

### 502 Bad Gateway
Ensure Immich is running and reachable at the host:port configured in the Cloudflare tunnel public hostname settings.

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [Immich Remote Access Guide](https://docs.immich.app/guides/remote-access/)
- [Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)
