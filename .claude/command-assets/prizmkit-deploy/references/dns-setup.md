# DNS Setup Guidance

Read this file when the user has a domain for their project but DNS is not yet pointing to the server.

## Step 1 — Check DNS resolution

```
dig +short <domain> A
```

If it resolves to the server IP: DNS is already configured, proceed to SSL (`references/ssl-setup.md`).
If not: continue below.

## Step 2 — DNS setup guidance

```
Domain <example.com> is not yet pointing to server <server-IP>.

Add the following record at your DNS provider (e.g., Alibaba Cloud, Cloudflare, Namecheap):

  Type:  A
  Name:  @
  Value: <server-IP>
  TTL:   600

To also support the www subdomain:
  Type:  A
  Name:  www
  Value: <server-IP>

Reply "done" when configured, and I'll verify and set up the SSL certificate.
```

## Step 3 — Verify after user confirmation

- Re-run `dig +short <domain> A` to confirm resolution.
- If still not resolved: warn about DNS propagation delay (can take up to 48 hours, usually 5-30 minutes). Offer to wait or continue without SSL for now.
- Once confirmed: proceed to SSL (`references/ssl-setup.md`).

## Edge case — IP-only deployment

If user has no domain: skip DNS + SSL sections. Generate a note in deploy.md: "Project accessed via IP, no domain or HTTPS configured. Recommend purchasing a domain and running `/prizmkit-deploy setup-ssl`."
