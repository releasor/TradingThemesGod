# SSL/HTTPS Configuration (Let's Encrypt + Certbot)

Read this file when DNS is confirmed pointing to the server and SSL needs to be configured.

## Step 1 — Detect cloud vendor

```
# Try metadata endpoints to detect cloud vendor
curl -s --connect-timeout 2 http://100.100.100.200/latest/meta-data/ && echo "ALIBABA"
curl -s --connect-timeout 2 http://metadata.tencentyun.com/latest/meta-data/ && echo "TENCENT"
curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/ && echo "AWS/GCP/AZURE"
```
Also check `/etc/hostname` for vendor patterns.

## Step 2 — Choose SSL strategy

- **Cloud vendor detected** → ask user:
  > "Detected the server is running on <cloud-vendor>. Which SSL approach?"
  > - **A. Let's Encrypt free certificate (recommended)** — one command for permanent auto-renewal, hassle-free
  > - **B. <cloud-vendor> native certificate** — manual download/config, 1-year validity requires manual renewal
  >
  > Choose A and I'll set it up for you; choose B and you'll need to download the certificate from the cloud console and tell me the path.
- **No cloud vendor / unknown** → use certbot directly, no choice needed.

## Step 3 — Certbot install & certificate request

```
# Install certbot (idempotent)
which certbot || apt-get install -y certbot python3-certbot-nginx

# Request certificate
certbot --nginx -d <domain> -d www.<domain> --non-interactive --agree-tos --email <user-email>
```

**Collect from user before running:**
- Email address (Let's Encrypt expiry notifications)
- Confirm domain list (e.g., `example.com, www.example.com`)

## Step 4 — Verify auto-renewal

```
systemctl status certbot.timer
certbot renew --dry-run
```
If timer is inactive, enable it: `systemctl enable --now certbot.timer`.

## Step 5 — Record

- Write SSL configuration summary to deploy.md: certificate paths, auto-renewal status, expiry date.
- Record a `"ssl-setup"` event in deploy history.

## Edge cases

- **DNS not yet propagated** → certbot challenge fails. Tell user to wait and retry: `/prizmkit-deploy setup-ssl`.
- **Existing certificate found** → check expiry date (`certbot certificates`). If expiring within 30 days, warn. Otherwise skip.
- **Port 80/443 occupied by non-Nginx process** → report and ask how to resolve before proceeding.
