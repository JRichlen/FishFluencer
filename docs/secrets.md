# Secrets Management

How FishFluencer handles API keys and other sensitive values without ever
committing them to the repository.

## Required Secrets

| Variable | Purpose | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API for post generation (text-only) | `src/social/post_generator.py` |

## Where Secrets Live (by environment)

### On the Coral Dev Board (production)

Secrets are stored in a systemd environment file that is **never checked into
git**:

```
/etc/fishfluencer/env          # mode 0600, owned by root
```

The systemd service loads it automatically:

```ini
# systemd/fishfluencer.service
EnvironmentFile=-/etc/fishfluencer/env
```

Create or update the file:

```bash
sudo mkdir -p /etc/fishfluencer
echo "ANTHROPIC_API_KEY=sk-ant-your-key" | sudo tee /etc/fishfluencer/env
sudo chmod 600 /etc/fishfluencer/env
sudo systemctl restart fishfluencer
```

### In GitHub Actions (CI / automated fixes)

Secrets are stored as **GitHub repository secrets** and injected into workflow
runs by GitHub. They never appear in logs or artifacts.

```yaml
# .github/workflows/auto-fix.yml
anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

To add or rotate a secret:

1. Go to **Settings → Secrets and variables → Actions** in the GitHub repo
2. Click **New repository secret** (or update an existing one)
3. Name: `ANTHROPIC_API_KEY`, Value: your key

### Local development

Copy the template and fill in your key:

```bash
cp .env.example .env
# Edit .env with your actual key
```

The config loader (`src/utils/config.py`) automatically reads `.env` if it
exists. Variables already set in the real environment (e.g. via `export`) take
precedence, so `.env` never overrides explicit settings.

`.env` is listed in `.gitignore` and will never be committed.

## Remote Secret Rotation (without SSH)

Because the Coral Dev Board uses outbound-only HTTPS (no SSH, no VPN), secrets
must be rotated through one of these methods:

### Option A — Manual access (easiest)

If you have physical or MDT/serial access to the device:

```bash
sudo nano /etc/fishfluencer/env   # update the key
sudo systemctl restart fishfluencer
```

### Option B — GitHub Actions deployment (recommended for remote)

Use a **repository dispatch** workflow to rotate the secret on-device via the
existing GitHub sync mechanism:

1. Store the new API key as a **GitHub repository secret**
   (`ANTHROPIC_API_KEY`)
2. Trigger the `deploy-secret.yml` workflow (via the Actions tab or the API)
3. On the next sync cycle, the device picks up the rotated value

This works because the sync agent already pulls from GitHub periodically. The
workflow writes an **encrypted** secret bundle that only the device can read.

> **Note:** The device must have a pre-shared decryption key created during
> initial setup. See the setup in `scripts/setup.sh`.

### Option C — Secure environment endpoint

For fleet deployments, point the device at a secure HTTPS endpoint that
returns environment variables (authenticated by a device-specific token).
This is beyond the scope of the default setup but can be integrated into
the sync agent.

## Security Checklist

- [x] API keys are **never** committed to the repository
- [x] `.env` and `.env.local` are in `.gitignore`
- [x] `/etc/fishfluencer/env` has `chmod 600` (root-only read)
- [x] Error reports are sanitized — `api_key`, `secret`, `password`, `token`
      fields are redacted before pushing to GitHub (`src/sync/log_pusher.py`)
- [x] GitHub Actions secrets are masked in workflow logs
- [x] The config loader resolves `${VAR}` at runtime, so placeholder values
      in `config/default.yaml` are harmless
- [x] No images or binary data ever leave the device — only text summaries
