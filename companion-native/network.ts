/** LAN / Tailscale IPs use Caddy tls internal; native fetch/WebView need plain HTTP. */

function isPrivateOrTailnetHost(host: string): boolean {
  if (!host || host === "localhost" || host.endsWith(".local")) return true;
  const m = host.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)$/);
  if (!m) return false;
  const a = Number(m[1]);
  const b = Number(m[2]);
  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  if (a === 127) return true;
  return false;
}

/** Use http:// for private/tailnet hosts so iOS does not reject tls internal. */
export function httpOriginIfPrivate(url: string): string {
  try {
    const u = new URL(url.includes("://") ? url : `https://${url}`);
    if (isPrivateOrTailnetHost(u.hostname)) {
      u.protocol = "http:";
      return u.origin;
    }
    return u.origin;
  } catch {
    return url.replace(/\/$/, "");
  }
}
