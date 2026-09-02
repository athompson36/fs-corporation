#!/usr/bin/env bash
# Sync this Mac checkout to fs-dev and prepare /Data/fs-corporation for install.
# Does not run sudo install — prints the final command (needs your password on the host).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${FS_CORP_FS_DEV_HOST:-andrew@192.168.4.100}"
REMOTE_DATA="${FS_CORP_REMOTE_DATA:-/Data/fs-corporation/data}"
REMOTE_APP="${FS_CORP_REMOTE_APP:-/opt/fs-corporation}"
SMB_LINK="${FS_CORP_SMB_LINK:-/media/andrew/Data/fs-corporation}"

# The deploy tree must NOT live on /Data: that mount is NTFS forced to 0777 and
# is re-exported over SMB, so a root-executed script or a staged private key
# there is writable/readable by every local user and every share client.
REMOTE_HOME="$(ssh -o BatchMode=yes "$HOST" 'printf %s "$HOME"')"
DEPLOY_ROOT="${FS_CORP_DEPLOY_ROOT:-$REMOTE_HOME/fs-corporation-deploy}"
REMOTE_REPO="${FS_CORP_REMOTE_REPO:-$DEPLOY_ROOT/repo}"
STAGE="$DEPLOY_ROOT/secrets-staging"

echo "==> Target host: $HOST"
echo "==> Deploy tree: $DEPLOY_ROOT (ext4, mode 700 — off the SMB share)"
echo "==> Repo: $REMOTE_REPO"
echo "==> App:  $REMOTE_APP"
echo "==> Data: $REMOTE_DATA (big disk /Data; Mac SMB bind → $SMB_LINK)"

ssh -o BatchMode=yes "$HOST" "mkdir -p '$REMOTE_REPO' '$STAGE' '$REMOTE_DATA/worker-scratch' '$REMOTE_DATA/companion' && chmod 700 '$DEPLOY_ROOT' '$STAGE'"

echo "==> rsync repository"
rsync -az --delete \
  --exclude '.venv/' \
  --exclude '.local/' \
  --exclude 'companion/node_modules/' \
  --exclude 'companion-native/node_modules/' \
  --exclude 'companion/dist/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'secrets/' \
  --exclude 'fs-corporation/' \
  "$ROOT/" "$HOST:$REMOTE_REPO/"

echo "==> Write env.prepared"
ssh -o BatchMode=yes "$HOST" "cat > $DEPLOY_ROOT/env.prepared <<EOF
FS_CORP_INSTALL_DIR=${REMOTE_APP}
FS_CORP_DATA_DIR=${REMOTE_DATA}
FS_CORP_DB=${REMOTE_DATA}/company.db
FS_CORP_TOKEN_FILE=/etc/fs-corporation/owner.token
FS_CORP_API_HOST=127.0.0.1
FS_CORP_API_PORT=8000
FS_CORP_COMPANION_DIST=${REMOTE_DATA}/companion/dist
FS_CORP_LAN_IP=192.168.4.100
FS_CORP_WORKER_NIC_IP=192.168.4.101
FS_CORP_WORKER_SCRATCH=${REMOTE_DATA}/worker-scratch
FS_CORP_WORKER_IMAGE=fs-corporation-worker:local
FS_CORP_DEFAULT_WORKER_RUNTIME=container
FS_CORP_PUBLIC_URL=https://192.168.4.100
EOF"

echo "==> Stage secrets"
if [[ -f "$ROOT/secrets/github-app.pem" ]]; then
  scp -q "$ROOT/secrets/github-app.pem" "$HOST:$STAGE/github-app.pem"
fi
if [[ -f "$ROOT/secrets/vapid-private.pem" ]]; then
  scp -q "$ROOT/secrets/vapid-public.pem" "$HOST:$STAGE/vapid-public.pem"
  scp -q "$ROOT/secrets/vapid-private.pem" "$HOST:$STAGE/vapid-private.pem"
fi
python3 <<'PY'
from pathlib import Path
root = Path("/Users/andrew/Documents/FS-Tech/fs-corporation")
env = {}
for line in (root / ".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip("'\"")
lines = []
for k in ("GITHUB_APP_ID", "GITHUB_INSTALLATION_ID", "MODEL_PROVIDER_API_KEY", "ANTHROPIC_API_KEY"):
    if env.get(k):
        lines.append(f"{k}={env[k]}")
if (root / "secrets/github-app.pem").is_file():
    lines.append("GITHUB_PRIVATE_KEY_FILE=/etc/fs-corporation/github-app.pem")
if (root / "secrets/vapid-private.pem").is_file():
    lines += [
        "VAPID_PUBLIC_KEY_FILE=/etc/fs-corporation/vapid-public.pem",
        "VAPID_PRIVATE_KEY_FILE=/etc/fs-corporation/vapid-private.pem",
        "VAPID_CONTACT_EMAIL=" + (env.get("VAPID_CONTACT_EMAIL") or "mailto:owner@example.com"),
    ]
Path("/tmp/fs-corp-secrets.env").write_text("\n".join(lines) + "\n")
print(f"staged {len(lines)} secret lines")
PY
scp -q /tmp/fs-corp-secrets.env "$HOST:$STAGE/secrets.env"
rm -f /tmp/fs-corp-secrets.env
ssh -o BatchMode=yes "$HOST" "chmod 600 $STAGE/*"

echo "==> Write run-install.sh on host"
ssh -o BatchMode=yes "$HOST" "cat > $DEPLOY_ROOT/run-install.sh <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
# sudo bash $DEPLOY_ROOT/run-install.sh
bash $DEPLOY_ROOT/repo/scripts/fix_fs_dev_apt.sh
# The app tree must stay on ext4: venv creation and npm both fail on NTFS.
export FS_CORP_INSTALL_DIR=/opt/fs-corporation
export FS_CORP_DATA_DIR=/Data/fs-corporation/data
export FS_CORP_DB=/Data/fs-corporation/data/company.db
export FS_CORP_COMPANION_DIST=/Data/fs-corporation/data/companion/dist
export FS_CORP_TOKEN_FILE=/etc/fs-corporation/owner.token
export FS_CORP_WORKER_SCRATCH=/Data/fs-corporation/data/worker-scratch
if id fs-corp &>/dev/null; then
  usermod -d /opt/fs-corporation fs-corp || true
fi
rm -rf /Data/fs-corporation/app/.npm /Data/fs-corporation/app/.npm-cache || true
cd $DEPLOY_ROOT/repo
bash deploy/fs-dev/install.sh
install -o root -g fs-corp -m 640 $DEPLOY_ROOT/env.prepared /etc/fs-corporation/env
if [[ -f $STAGE/secrets.env ]]; then
  install -o root -g fs-corp -m 640 $STAGE/secrets.env /etc/fs-corporation/secrets.env
fi
# 640 root:fs-corp, not 600: the API runs as fs-corp and reads these key files.
for f in github-app.pem vapid-public.pem vapid-private.pem; do
  if [[ -f $STAGE/\$f ]]; then
    install -o root -g fs-corp -m 640 \"$STAGE/\$f\" \"/etc/fs-corporation/\$f\"
  fi
done
# Keys live in /etc/fs-corporation from here on; do not leave copies staged.
shred -u $STAGE/* 2>/dev/null || rm -f $STAGE/*
mkdir -p /media/andrew/Data/fs-corporation
if ! findmnt /media/andrew/Data/fs-corporation >/dev/null 2>&1; then
  mount --bind /Data/fs-corporation /media/andrew/Data/fs-corporation
fi
if ! grep -q '/media/andrew/Data/fs-corporation' /etc/fstab; then
  echo '/Data/fs-corporation /media/andrew/Data/fs-corporation none bind 0 0' >> /etc/fstab
fi
chown -R fs-corp:fs-corp /Data/fs-corporation/data 2>/dev/null || true
systemctl restart fs-corporation-api
echo
echo 'Owner token file: /etc/fs-corporation/owner.token'
for _ in \$(seq 1 20); do
  code=\$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/v1/health 2>/dev/null || echo 000)
  [[ \"\$code\" == 200 ]] && break
  sleep 1
done
echo \"loopback health: \$code\"
curl -k -sS -o /dev/null -w 'https edge: %{http_code}\\n' https://192.168.4.100/ || true
EOS
chmod 700 $DEPLOY_ROOT/run-install.sh"

echo "==> Write restricted sudoers candidate"
REMOTE_USER="${HOST%@*}"
ssh -o BatchMode=yes "$HOST" "cat > $DEPLOY_ROOT/nopasswd.sudoers <<EOS
# Passwordless sudo for fs-corporation deploy.
# run-install.sh must stay on a filesystem only this user can write. Never point
# this rule at /Data: that mount is 0777 and re-exported over SMB, which would
# let any share client execute arbitrary code as root.
$REMOTE_USER ALL=(ALL) NOPASSWD: /bin/bash $DEPLOY_ROOT/run-install.sh
$REMOTE_USER ALL=(ALL) NOPASSWD: /bin/bash $DEPLOY_ROOT/rotate-owner-token.sh
$REMOTE_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart fs-corporation-api
$REMOTE_USER ALL=(ALL) NOPASSWD: /bin/systemctl status fs-corporation-api
$REMOTE_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart caddy
$REMOTE_USER ALL=(ALL) NOPASSWD: /usr/bin/journalctl -u fs-corporation-api *
EOS
chmod 600 $DEPLOY_ROOT/nopasswd.sudoers"

echo "==> Write rotate-owner-token.sh on host"
ssh -o BatchMode=yes "$HOST" "cat > $DEPLOY_ROOT/rotate-owner-token.sh <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
# sudo bash $DEPLOY_ROOT/rotate-owner-token.sh
# Rotates /etc/fs-corporation/owner.token and writes a mode-600 copy for andrew.
COPY=$DEPLOY_ROOT/owner.token.rotated
/opt/fs-corporation/.venv/bin/python /opt/fs-corporation/scripts/rotate_owner_token.py \\
  --db /Data/fs-corporation/data/company.db \\
  --token-file /etc/fs-corporation/owner.token \\
  --write-token-copy \"\$COPY\"
chown andrew:andrew \"\$COPY\"
chmod 600 \"\$COPY\"
systemctl restart fs-corporation-api
echo \"New token copy (mode 600): \$COPY\"
echo \"Shred that file after you have stored the token somewhere safe.\"
EOS
chmod 700 $DEPLOY_ROOT/rotate-owner-token.sh"

cat <<EOF

Prepared on $HOST under $DEPLOY_ROOT (mode 700, ext4).

If the sudoers rule still points at /Data, replace it (one password prompt):

  ssh -t $HOST 'sudo install -o root -g root -m 440 \\
    $DEPLOY_ROOT/nopasswd.sudoers /etc/sudoers.d/andrew-fs-corporation \\
    && sudo visudo -cf /etc/sudoers.d/andrew-fs-corporation'

Then install:

  ssh $HOST 'sudo bash $DEPLOY_ROOT/run-install.sh'

Then open https://192.168.4.100 and check the Mac share:
  /Volumes/fs-dev-data/fs-corporation

EOF
