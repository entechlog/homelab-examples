#!/bin/sh
# Generate serve.json from environment variables
cat > /config/serve.json <<EOF
{
  "TCP": {
    "443": {
      "HTTPS": true
    }
  },
  "Web": {
    "\${TS_CERT_DOMAIN}:443": {
      "Handlers": {
        "/": {
          "Proxy": "http://${IMMICH_HOST:-localhost}:${IMMICH_PORT:-2283}"
        }
      }
    }
  }
}
EOF

exec /usr/local/bin/containerboot
