/** TailscaleKit / userspace VPN stub — not available in store builds yet. */

export function isTailscaleKitAvailable(): boolean {
  return false;
}

export async function joinWithAuthKey(
  _key: string
): Promise<{ ok: false; reason: "not_implemented" }> {
  return { ok: false, reason: "not_implemented" };
}
