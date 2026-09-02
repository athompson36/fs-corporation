#!/usr/bin/env bash
# Enable passwordless sudo on fs-dev for deploy/restart commands (one password prompt).
set -euo pipefail
HOST="${FS_CORP_FS_DEV_HOST:-andrew@192.168.4.100}"

echo "==> SSH public-key login (already required)"
ssh -o PreferredAuthentications=publickey -o BatchMode=yes "$HOST" 'echo OK: pubkey login as $(whoami)@$(hostname)'

echo "==> Install restricted sudoers (enter sudo password once)"
ssh -t "$HOST" 'sudo install -o root -g root -m 440 /Data/fs-corporation/andrew-nopasswd.sudoers /etc/sudoers.d/andrew-fs-corporation && sudo visudo -cf /etc/sudoers.d/andrew-fs-corporation && echo OK: passwordless sudo for run-install / systemctl'

echo "==> Verify passwordless sudo"
ssh -o BatchMode=yes "$HOST" 'sudo -n true && echo OK: sudo -n works || echo FAIL: sudo still needs a password'

echo
echo "You can now run:"
echo "  ssh $HOST 'sudo bash /Data/fs-corporation/run-install.sh'"
