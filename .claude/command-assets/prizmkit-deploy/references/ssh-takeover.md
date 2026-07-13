# SSH: Existing Deployment Takeover

When deploying to a server that already has deployment assets.

## Detection

1. Check for existing `/var/www/<project>` directory
2. Check for existing PM2 processes with similar names
3. Check Nginx config referencing the same domain/IP
4. Check for port conflicts

## Decision Flow

Report findings and ask for takeover decision:

- **Take over and backup**: Back up existing config, then proceed.
- **Coexist**: Use different directory/ports/process names.
- **Manual resolve**: Stop and let the user handle it.

Record takeover decision and validation results in config and history.
