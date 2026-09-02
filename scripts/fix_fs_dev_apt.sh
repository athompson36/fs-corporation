#!/usr/bin/env bash
# One-shot apt repair for fs-dev (run with sudo). Safe to re-run.
set -euo pipefail
codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
ds=/etc/apt/sources.list.d/docker.sources
if [[ -f "$ds" ]] && grep -q '\$(' "$ds"; then
  echo "Fixing $ds Suites → $codename"
  sed -i "s|^Suites:.*|Suites: ${codename}|" "$ds"
fi
if [[ -f /etc/apt/sources.list.d/docker.sources && -f /etc/apt/sources.list.d/docker.list ]]; then
  echo "Disabling duplicate docker.list"
  mv -f /etc/apt/sources.list.d/docker.list /etc/apt/sources.list.d/docker.list.disabled
fi
if [[ -f /etc/apt/sources.list.d/github-cli.list && ! -s /usr/share/keyrings/githubcli-archive-keyring.gpg ]]; then
  echo "Disabling github-cli.list (empty keyring)"
  mv -f /etc/apt/sources.list.d/github-cli.list /etc/apt/sources.list.d/github-cli.list.disabled
fi
apt-get update -qq
echo "apt-get update OK"
