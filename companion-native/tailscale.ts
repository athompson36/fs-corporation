import { Linking, Platform } from "react-native";

/** Tailscale app URL scheme (iOS + Android when installed). */
export const TAILSCALE_APP = "tailscale://";

export const TAILSCALE_STORE =
  Platform.OS === "android"
    ? "https://play.google.com/store/apps/details?id=com.tailscale.ipn"
    : "https://apps.apple.com/app/tailscale/id1470499037";

/** One-paste auth-key instructions shown after clipboard copy. */
export function authKeyInstructions(): string {
  if (Platform.OS === "android") {
    return (
      "Auth key copied. In Tailscale: account menu → Log in → Use an auth key → Paste. " +
      "Then return here."
    );
  }
  return (
    "Auth key copied. In Tailscale: profile → Log in → (…) → Use an auth key → Paste. " +
    "Then return here."
  );
}

export async function openTailscaleApp(): Promise<void> {
  try {
    const can = await Linking.canOpenURL(TAILSCALE_APP);
    await Linking.openURL(can ? TAILSCALE_APP : TAILSCALE_STORE);
  } catch {
    await Linking.openURL(TAILSCALE_STORE);
  }
}
