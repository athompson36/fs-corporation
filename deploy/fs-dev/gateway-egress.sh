#!/usr/bin/env bash
# Policy-route fs-corp API egress via the worker NIC (FS_CORP_WORKER_NIC_IP).
# Usage: gateway-egress.sh apply|remove|status
# Requires root for apply/remove. Status is read-only.
set -euo pipefail

TABLE="${FS_CORP_GATEWAY_EGRESS_TABLE:-101}"
PRIORITY="${FS_CORP_GATEWAY_EGRESS_PRIORITY:-1000}"
SERVICE_USER="${FS_CORP_SERVICE_USER:-fs-corp}"
NIC_IP="${FS_CORP_WORKER_NIC_IP:-}"

die() { echo "gateway-egress: $*" >&2; exit 1; }

require_root() {
  [[ "$(id -u)" -eq 0 ]] || die "apply/remove require root"
}

resolve_uid() {
  id -u "${SERVICE_USER}" 2>/dev/null || die "user ${SERVICE_USER} not found"
}

iface_for_ip() {
  local ip="$1" line
  while IFS= read -r line; do
    if [[ "$line" == *" ${ip}/"* ]]; then
      awk '{print $2}' <<<"$line" | tr -d ':'
      return 0
    fi
  done < <(ip -4 -o addr show 2>/dev/null || true)
  return 1
}

prefix_for_ip() {
  local ip="$1" line
  while IFS= read -r line; do
    if [[ "$line" == *" ${ip}/"* ]]; then
      awk '{for(i=1;i<=NF;i++) if($i=="inet"){print $(i+1); exit}}' <<<"$line"
      return 0
    fi
  done < <(ip -4 -o addr show 2>/dev/null || true)
  return 1
}

network_for_cidr() {
  python3 -c "import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]).network)" "$1"
}

default_gateway() {
  ip -4 route show default 2>/dev/null | awk '/^default/ {print $3; exit}'
}

rule_exists() {
  local uid="$1"
  ip -4 rule list | grep -q "uidrange ${uid}-${uid} lookup ${TABLE}"
}

flush_policy() {
  local uid=""
  if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    uid=$(id -u "${SERVICE_USER}")
    while rule_exists "${uid}"; do
      ip -4 rule del uidrange "${uid}-${uid}" lookup "${TABLE}" priority "${PRIORITY}" 2>/dev/null \
        || ip -4 rule del uidrange "${uid}-${uid}" lookup "${TABLE}" 2>/dev/null \
        || break
    done
  fi
  ip -4 route flush table "${TABLE}" 2>/dev/null || true
}

cmd_status() {
  local uid="" mode="default" present="false" active="false" iface="" src=""
  if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    uid=$(id -u "${SERVICE_USER}")
  fi
  if [[ -n "${NIC_IP}" ]] && iface=$(iface_for_ip "${NIC_IP}"); then
    present="true"
  else
    iface=""
  fi
  if [[ "${FS_CORP_GATEWAY_EGRESS:-default}" == "worker_nic" ]]; then
    mode="worker_nic"
  fi
  if [[ -n "${uid}" ]] && rule_exists "${uid}"; then
    src=$(ip -4 route show table "${TABLE}" 2>/dev/null | awk '/^default/ {for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')
    if ip -4 route show table "${TABLE}" 2>/dev/null | grep -q '^default'; then
      active="true"
    fi
  fi
  printf 'mode=%s worker_nic_ip=%s worker_nic_present=%s egress_active=%s egress_table=%s egress_source_ip=%s iface=%s\n' \
    "${mode}" "${NIC_IP:-}" "${present}" "${active}" "${TABLE}" "${src:-}" "${iface:-}"
  if [[ "${mode}" == "worker_nic" && "${active}" != "true" ]]; then
    return 2
  fi
  return 0
}

cmd_remove() {
  require_root
  flush_policy
  echo "gateway-egress: removed table ${TABLE} / uid rules for ${SERVICE_USER}"
}

cmd_apply() {
  require_root
  [[ -n "${NIC_IP}" ]] || die "FS_CORP_WORKER_NIC_IP is required for apply"
  local uid iface cidr net gw
  uid=$(resolve_uid)
  iface=$(iface_for_ip "${NIC_IP}") || die "FS_CORP_WORKER_NIC_IP=${NIC_IP} is not assigned on this host"
  cidr=$(prefix_for_ip "${NIC_IP}") || die "could not resolve prefix for ${NIC_IP}"
  net=$(network_for_cidr "${cidr}")
  gw=$(default_gateway) || true
  [[ -n "${gw}" ]] || die "no default gateway found"

  flush_policy
  ip -4 route replace "${net}" dev "${iface}" src "${NIC_IP}" table "${TABLE}"
  ip -4 route replace default via "${gw}" dev "${iface}" src "${NIC_IP}" table "${TABLE}"
  ip -4 rule add uidrange "${uid}-${uid}" lookup "${TABLE}" priority "${PRIORITY}"
  echo "gateway-egress: applied uid=${uid} table=${TABLE} iface=${iface} src=${NIC_IP} via=${gw}"

  local probe
  probe=$(sudo -u "${SERVICE_USER}" ip -4 route get 1.1.1.1 2>/dev/null || true)
  if ! grep -q "dev ${iface}" <<<"${probe}"; then
    die "post-apply check failed: expected dev ${iface}; got: ${probe}"
  fi
  if ! grep -q "src ${NIC_IP}" <<<"${probe}"; then
    die "post-apply check failed: expected src ${NIC_IP}; got: ${probe}"
  fi
}

case "${1:-}" in
  apply) cmd_apply ;;
  remove) cmd_remove ;;
  status) cmd_status ;;
  *) die "usage: $0 apply|remove|status" ;;
esac
