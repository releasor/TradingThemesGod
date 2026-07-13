# SSH Bootstrap Flow

Bootstraps the server before first deployment. Present a plan showing every privileged action before executing anything.

## Always-Run Preflight

```
locale-gen en_US.UTF-8           # fix locale warnings on bare Ubuntu
apt-get update -qq               # refresh package list
```

## Check-and-Install (idempotent)

Node.js, npm, PM2, Nginx, Git. Use v22 LTS if v25 not available.

## Detect Port Conflicts

`ss -tlnp | grep :80 || true`. If port 80/443 is occupied, report and ask how to resolve.

## User and Directory Setup

```
useradd -m -s /bin/bash <runtimeUser>   # if not exists
mkdir -p /var/www/<project>/{releases,shared,deploy-logs}
chown -R <runtimeUser>:<runtimeUser> /var/www/<project>
```

## PM2 Startup

```
env PATH=$PATH:/usr/bin pm2 startup systemd -u <runtimeUser> --hp /home/<runtimeUser>
```

## Deploy Key (Pull mode only)

```
sudo -u <runtimeUser> ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
sudo -u <runtimeUser> ssh-keyscan -H github.com >> ~/.ssh/known_hosts
```

## Security Baseline (Firewall)

After core tools are installed, ask whether to configure ufw. If user agrees, read `references/firewall-setup.md` for the full interactive flow and rule templates.

## Database Setup

If Discovery detected database drivers, ask whether to install the database on the server. If user agrees, read `references/database-setup.md` for platform-specific setup commands and security notes.

After each bootstrap step, record the result. Bootstrap operations must be idempotent. Back up any existing config files before modifying them.
