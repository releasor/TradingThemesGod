# Firewall Setup (UFW)

Read this file when the user wants AI-assisted firewall configuration during bootstrap.

## Flow

1. After core tools are installed, ask the user:
   > "Want me to configure the firewall (ufw)? Only necessary ports will be opened, improving server security."

2. If user declines: skip, record to deploy config.

3. If user agrees, ask which additional ports to open (beyond SSH/HTTP/HTTPS):
   > "By default only SSH(22), HTTP(80), HTTPS(443) are opened. Should the blue/green preview ports (3101/3102) also be opened? If you need other ports (e.g., for remote database management), list them together."

4. Collect ports, then ask:
   > "Firewall rules are ready. Should I apply them directly, or will you do it yourself?"
   > - **A. You apply them** — AI runs ufw commands
   > - **B. I'll do it myself** — output rule list, user executes manually

## Planned rules (output before executing)

```
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp       # SSH
ufw allow 80/tcp       # HTTP
ufw allow 443/tcp      # HTTPS
ufw allow 3101/tcp     # blue preview (user-approved)
ufw allow 3102/tcp     # green preview (user-approved)
ufw --force enable
```

## Rules for automatic execution

- Check `ufw status` first — if rules already exist, append only missing rules, don't overwrite.
- Never `ufw reset` unless explicitly asked, because it wipes custom rules the user may have configured manually.
- Record a `"security-baseline"` event in deploy history with the rule list, so future sessions can detect existing configuration.
