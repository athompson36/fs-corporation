import { useState } from "react";
import { SafeAreaView, TextInput, Button, StyleSheet, Text } from "react-native";
import { WebView } from "react-native-webview";

const DEFAULT_URL = process.env.EXPO_PUBLIC_PWA_URL ?? "http://127.0.0.1:5173";

export default function App() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [loaded, setLoaded] = useState(DEFAULT_URL);

  return (
    <SafeAreaView style={styles.root}>
      <Text style={styles.label}>PWA URL (Tailscale or local dev)</Text>
      <TextInput style={styles.input} value={url} onChangeText={setUrl} autoCapitalize="none" />
      <Button title="Load" onPress={() => setLoaded(url)} />
      <WebView source={{ uri: loaded }} style={styles.web} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#111" },
  label: { color: "#aaa", padding: 8, fontSize: 12 },
  input: { marginHorizontal: 8, padding: 8, backgroundColor: "#222", color: "#eee", borderRadius: 6 },
  web: { flex: 1, marginTop: 8 },
});
