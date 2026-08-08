# Dead Signal

Dead Signal is a community-first Once Human build planner. The current production bundle is deployed to Namecheap/cPanel from this repository.

## Deployment layout

- `.cpanel.yml` contains the cPanel deployment recipe.
- `deploy/site.b64.part*` contains the production site bundle split into text-safe parts.
- cPanel reconstructs the bundle and extracts it into `$HOME/public_html` when **Deploy HEAD Commit** is run.

## One-time Namecheap/cPanel setup

This repository is private, so cPanel needs a dedicated read-only GitHub SSH deploy key.

1. In cPanel, open **Terminal** and run:

   ```bash
   mkdir -p ~/.ssh
   chmod 700 ~/.ssh
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/dead-signal -C "dead-signal-deploy"
   cat ~/.ssh/dead-signal.pub
   ```

   For this dedicated read-only deployment key, leave the passphrase blank so cPanel can pull without an interactive prompt.

2. Copy the full public key printed by the last command.
3. In GitHub open **raiinman/dead-signal → Settings → Deploy keys → Add deploy key**.
   - Title: `Namecheap cPanel`
   - Paste the public key.
   - Leave **Allow write access** unchecked.
4. Back in cPanel Terminal, configure SSH to use that key for GitHub:

   ```bash
   cat > ~/.ssh/config <<'EOF'
   Host github.com
     HostName github.com
     User git
     IdentityFile ~/.ssh/dead-signal
     IdentitiesOnly yes
   EOF
   chmod 600 ~/.ssh/config
   ssh -T git@github.com
   ```

5. In **cPanel → Files → Git Version Control → Create**:
   - Clone a Repository: **On**
   - Clone URL: `git@github.com:raiinman/dead-signal.git`
   - Repository Path: `repositories/dead-signal`
   - Repository Name: `Dead Signal`
6. Create the repository.
7. Open **Manage → Pull or Deploy**.
8. Click **Update from Remote** and then **Deploy HEAD Commit**.

The current `.cpanel.yml` deploys to the main account document root: `$HOME/public_html`.

> If Dead Signal should live in a subdomain/addon-domain document root instead, change `DEPLOYPATH` in `.cpanel.yml` before deploying.

## Normal update flow

After the one-time setup:

1. Update this GitHub repository.
2. In cPanel Git Version Control click **Update from Remote**.
3. Click **Deploy HEAD Commit**.

The site files in `public_html` are overwritten as needed; the deployment script does not wipe unrelated files.
