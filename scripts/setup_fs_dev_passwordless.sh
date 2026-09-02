#!/usr/bin/env bash
# Enable passwordless sudo on fs-dev for deploy/restart commands (one password prompt).
# Run scripts/deploy_to_fs_dev.sh first: it writes the sudoers candidate.
set -euo pipefail
HOST="${FS_CORP_FS_DEV_HOST:-andrew@192.168.4.100}"

echo "==> SSH public-key login (already required)"
ssh -o PreferredAuthentications=publickey -o BatchMode=yes "$HOST" 'echo OK: pubkey login as $(whoami)@$(hostname)'

REMOTE_HOME="$(ssh -o BatchMode=yes "$HOST" 'printf %s "$HOME"')"
DEPLOY_ROOT="${FS_CORP_DEPLOY_ROOT:-$REMOTE_HOME/fs-corporation-deploy}"
CANDIDATE="$DEPLOY_ROOT/nopasswd.sudoers"

if ! ssh -o BatchMode=yes "$HOST" "test -f '$CANDIDATE'"; then
  echo "Missing $CANDIDATE on $HOST — run scripts/deploy_to_fs_dev.sh first." >&2
  exit 1
fi

# The granted script must not be writable by anyone but this user, or the rule
# becomes a local root escalation. /Data is 0777 and SMB-exported, so refuse it.
echo "==> Checking the granted script is on a safe filesystem"
ssh -o BatchMode=yes "$HOST" "
  set -e
  case '$DEPLOY_ROOT' in
    /Data/*|/media/*|/mnt/*)
      echo 'REFUSING: $DEPLOY_ROOT looks like a removable or shared mount.' >&2; exit 1;;
  esac
  fstype=\$(findmnt -no FSTYPE --target '$DEPLOY_ROOT')
  case \"\$fstype\" in
    ext2|ext3|ext4|xfs|btrfs) ;;
    *) echo \"REFUSING: \$fstype cannot enforce file permissions.\" >&2; exit 1;;
  esac
  perms=\$(stat -c %a '$DEPLOY_ROOT/run-install.sh')
  case \"\$perms\" in
    700|750|755) ;;
    *) echo \"REFUSING: run-install.sh is mode \$perms; expected 700.\" >&2; exit 1;;
  esac
  echo \"OK: \$fstype, run-install.sh mode \$perms\"
"

echo "==> Install restricted sudoers (enter sudo password once)"
ssh -t "$HOST" "sudo install -o root -g root -m 440 '$CANDIDATE' /etc/sudoers.d/andrew-fs-corporation \
  && sudo visudo -cf /etc/sudoers.d/andrew-fs-corporation"

echo "==> Verify the granted command is allowed without a password"
ssh -o BatchMode=yes "$HOST" "sudo -n -l /bin/bash '$DEPLOY_ROOT/run-install.sh' >/dev/null \
  && echo 'OK: passwordless run-install' || echo 'FAIL: sudo still needs a password'"

echo
echo "You can now run:"
echo "  ssh $HOST 'sudo bash $DEPLOY_ROOT/run-install.sh'"
