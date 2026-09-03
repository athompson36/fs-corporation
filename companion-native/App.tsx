import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { WebView } from "react-native-webview";
import * as Clipboard from "expo-clipboard";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { httpOriginIfPrivate } from "./network";

const STORAGE_KEY = "fs-corp-native-session";
const TAILSCALE_APP = "tailscale://";
const TAILSCALE_STORE = "https://apps.apple.com/app/tailscale/id1470499037";

type Session = {
  token: string;
  baseUrl: string;
  companionUrl: string;
  accessLevel?: string;
  label?: string;
};

type RedeemResponse = {
  token: string;
  base_url?: string;
  companion_url?: string;
  access_level?: string;
  label?: string;
  scopes?: string[];
  tailscale_auth_key?: string;
  vpn?: { provider?: string; status?: string; ios_handoff?: string };
};

function ticketFromText(raw: string): { origin: string; ticket: string } | null {
  const text = raw.trim();
  const hash = text.match(/#fs-pair=([^&\s]+)/);
  if (hash) {
    try {
      const u = new URL(text.includes("://") ? text : `https://placeholder.local/${text}`);
      const origin = text.includes("://") ? `${u.protocol}//${u.host}` : "";
      return { origin, ticket: decodeURIComponent(hash[1]) };
    } catch {
      return { origin: "", ticket: decodeURIComponent(hash[1]) };
    }
  }
  if (/^[A-Za-z0-9_-]{20,}$/.test(text)) {
    return { origin: "", ticket: text };
  }
  return null;
}

async function redeem(origin: string, ticket: string): Promise<RedeemResponse> {
  const base = httpOriginIfPrivate(origin.replace(/\/$/, ""));
  const r = await fetch(`${base}/api/v1/remote-access/redeem`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload: { ticket } }),
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json();
}

async function waitForCompanion(url: string, token: string, attempts = 40): Promise<boolean> {
  const health = `${httpOriginIfPrivate(url)}/api/v1/health`;
  for (let i = 0; i < attempts; i++) {
    try {
      const r = await fetch(health, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (r.ok) return true;
    } catch {
      /* VPN not up yet */
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  return false;
}

export default function App() {
  const [paste, setPaste] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [webviewUrl, setWebviewUrl] = useState<string | null>(null);
  const polling = useRef(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((raw) => {
      if (!raw) return;
      try {
        const s = JSON.parse(raw) as Session;
        setSession(s);
        setWebviewUrl(s.companionUrl || s.baseUrl);
      } catch {
        /* ignore */
      }
    });
  }, []);

  const openTailscale = useCallback(async () => {
    const can = await Linking.canOpenURL(TAILSCALE_APP);
    await Linking.openURL(can ? TAILSCALE_APP : TAILSCALE_STORE);
  }, []);

  const runPair = useCallback(async () => {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const parsed = ticketFromText(paste);
      if (!parsed?.ticket) throw new Error("Paste the pair URL from the CEO desk QR (…/#fs-pair=…).");
      const origin = parsed.origin || "http://192.168.4.100";
      setStatus("Redeeming pairing ticket…");
      const data = await redeem(origin, parsed.ticket);
      const companion = httpOriginIfPrivate(data.companion_url || data.base_url || origin);
      const next: Session = {
        token: data.token,
        baseUrl: httpOriginIfPrivate(data.base_url || origin),
        companionUrl: companion,
        accessLevel: data.access_level,
        label: data.label,
      };
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setSession(next);

      if (data.tailscale_auth_key) {
        await Clipboard.setStringAsync(data.tailscale_auth_key);
        setStatus(
          "Auth key copied. In Tailscale: profile → Log in → (…) → Use an auth key → Paste. Then return here.",
        );
        await openTailscale();
        if (!polling.current) {
          polling.current = true;
          setStatus("Waiting for Tailscale companion URL…");
          const ok = await waitForCompanion(companion, data.token);
          polling.current = false;
          if (ok) {
            setStatus("Tailscale reachable.");
            setWebviewUrl(companion);
          } else {
            setError("Timed out waiting for Tailscale. Finish auth-key login, then tap Open companion.");
          }
        }
      } else {
        setWebviewUrl(next.baseUrl);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [paste, openTailscale]);

  if (webviewUrl && session) {
    const injected = `
      (function() {
        try {
          localStorage.setItem('fs-corp-companion-settings', JSON.stringify({
            baseUrl: '',
            token: ${JSON.stringify(session.token)},
            access_level: ${JSON.stringify(session.accessLevel || "")},
            label: ${JSON.stringify(session.label || "")}
          }));
        } catch (e) {}
      })();
      true;
    `;
    return (
      <SafeAreaView style={styles.root}>
        <View style={styles.bar}>
          <Text style={styles.barText} numberOfLines={1}>
            {webviewUrl}
          </Text>
          <TouchableOpacity onPress={() => setWebviewUrl(null)}>
            <Text style={styles.link}>Re-pair</Text>
          </TouchableOpacity>
        </View>
        <WebView
          source={{ uri: httpOriginIfPrivate(webviewUrl) }}
          style={styles.web}
          injectedJavaScriptBeforeContentLoaded={injected}
          // tls internal on fs-dev
          setSupportMultipleWindows={false}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.root}>
      <View style={styles.pad}>
        <Text style={styles.title}>FS-Corporation</Text>
        <Text style={styles.lede}>
          On home Wi‑Fi, paste the CEO desk pair URL. We redeem it, copy the Tailscale auth key, and open
          Tailscale for a one-paste join. Then the companion loads on the tailnet.
        </Text>
        <TextInput
          style={styles.input}
          value={paste}
          onChangeText={setPaste}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="https://192.168.4.100/#fs-pair=…"
          placeholderTextColor="#666"
          multiline
        />
        <TouchableOpacity style={styles.btn} onPress={runPair} disabled={busy}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Pair &amp; join VPN</Text>}
        </TouchableOpacity>
        {session ? (
          <TouchableOpacity
            style={styles.btnSecondary}
            onPress={() => setWebviewUrl(session.companionUrl || session.baseUrl)}
          >
            <Text style={styles.btnText}>Open companion</Text>
          </TouchableOpacity>
        ) : null}
        <TouchableOpacity style={styles.btnSecondary} onPress={openTailscale}>
          <Text style={styles.btnText}>Open Tailscale</Text>
        </TouchableOpacity>
        {status ? <Text style={styles.muted}>{status}</Text> : null}
        {error ? <Text style={styles.err}>{error}</Text> : null}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0b1020" },
  pad: { padding: 20, gap: 12 },
  title: { color: "#e8eefc", fontSize: 28, fontWeight: "700" },
  lede: { color: "#9aa8c7", fontSize: 14, lineHeight: 20 },
  input: {
    minHeight: 80,
    borderWidth: 1,
    borderColor: "#2a3550",
    borderRadius: 8,
    padding: 12,
    color: "#e8eefc",
    backgroundColor: "#121a2e",
  },
  btn: {
    backgroundColor: "#3d6df0",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  btnSecondary: {
    backgroundColor: "#1c2740",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
  },
  btnText: { color: "#fff", fontWeight: "600" },
  muted: { color: "#9aa8c7", fontSize: 13 },
  err: { color: "#ff8f8f", fontSize: 13 },
  bar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: "#121a2e",
  },
  barText: { color: "#9aa8c7", flex: 1, marginRight: 8, fontSize: 12 },
  link: { color: "#7aa2ff", fontWeight: "600" },
  web: { flex: 1 },
});
