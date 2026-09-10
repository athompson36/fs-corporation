import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { ApiClient } from "./api/client";
import { ModeSwitch, type PanelMode } from "./ModeSwitch";

type WorkersPanelProps = {
  api: ApiClient;
  hasToken: boolean;
  canPause: boolean;
  scopeNotice: (action: string, scope: string) => ReactNode;
  runAction: (key: string, okMessage: string, run: () => Promise<void>) => Promise<void>;
  status: (key: string) => ReactNode;
};

type IssuedToken = {
  hostId: string;
  label: string;
  token: string;
};

export function WorkersPanel(props: WorkersPanelProps) {
  const { api, hasToken, canPause, scopeNotice, runAction, status } = props;
  const [hosts, setHosts] = useState<Record<string, unknown>[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [issuedToken, setIssuedToken] = useState<IssuedToken | null>(null);
  const [mode, setMode] = useState<PanelMode>("browse");
  const tokenCodeRef = useRef<HTMLElement>(null);

  const loadAll = useCallback(async (isCancelled: () => boolean = () => false) => {
    if (!hasToken) return;
    try {
      const body = await api.workerHosts();
      if (isCancelled()) return;
      setHosts(body.hosts || []);
      setLoadError(null);
    } catch (error) {
      if (isCancelled()) return;
      setHosts([]);
      setLoadError(error instanceof Error ? error.message : String(error));
    }
  }, [api, hasToken]);

  useEffect(() => {
    let cancelled = false;
    void loadAll(() => cancelled);
    return () => {
      cancelled = true;
    };
  }, [loadAll]);

  async function createHost(event: FormEvent) {
    event.preventDefault();
    await runAction("worker-host-create", "Worker host created.", async () => {
      const response = await api.createWorkerHost(label.trim(), baseUrl.trim());
      setIssuedToken({
        hostId: response.result.id,
        label: response.result.label,
        token: response.result.token,
      });
      setLabel("");
      setBaseUrl("");
      await loadAll();
    });
  }

  async function setHostEnabled(hostId: string, enabled: boolean) {
    await runAction(
      `worker-host-${enabled ? "enable" : "disable"}-${hostId}`,
      `Worker host ${enabled ? "enabled" : "disabled"}.`,
      async () => {
        if (enabled) {
          await api.enableWorkerHost(hostId);
        } else {
          await api.disableWorkerHost(hostId);
        }
        await loadAll();
      },
    );
  }

  async function deleteHost(hostId: string) {
    if (!window.confirm("Delete this worker host? The host token will stop working.")) return;
    await runAction(`worker-host-delete-${hostId}`, "Worker host deleted.", async () => {
      await api.deleteWorkerHost(hostId);
      await loadAll();
    });
  }

  async function copyIssuedToken() {
    await runAction("worker-host-token-copy", "Worker host token copied.", async () => {
      if (!issuedToken) return;
      try {
        await navigator.clipboard.writeText(issuedToken.token);
      } catch {
        const code = tokenCodeRef.current;
        if (code) {
          const range = document.createRange();
          range.selectNodeContents(code);
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);
        }
        throw new Error("Clipboard unavailable; the token has been selected for manual copy.");
      }
    });
  }

  return (
    <section>
      <p className="lede">Registered remote worker hosts from persisted control-plane state.</p>
      <ModeSwitch mode={mode} onChange={setMode} label="Workers mode" />

      {mode === "browse" && (
        <>
          {loadError && <p className="error">Worker hosts could not be loaded: {loadError}</p>}

          <div className="card">
            <h2>Worker hosts</h2>
            {hosts.map((host) => {
              const id = String(host.id);
              const state = String(host.state);
              return (
                <div key={id} style={{ marginBottom: "1rem" }}>
                  <strong>{String(host.label)}</strong>
                  <div className="muted">Id: {id.length > 8 ? `${id.slice(0, 8)}…` : id}</div>
                  <div className="muted">URL: {String(host.base_url)}</div>
                  <div className="muted">State: {state}</div>
                  <div className="muted">
                    Last heartbeat: {host.last_heartbeat_at == null ? "—" : String(host.last_heartbeat_at)}
                  </div>
                  {canPause && (
                    <div className="actions">
                      <button
                        type="button"
                        onClick={() => void setHostEnabled(id, state === "disabled")}
                      >
                        {state === "disabled" ? "Enable" : "Disable"}
                      </button>
                      <button className="danger" type="button" onClick={() => void deleteHost(id)}>
                        Delete
                      </button>
                    </div>
                  )}
                  {status(`worker-host-enable-${id}`)}
                  {status(`worker-host-disable-${id}`)}
                  {status(`worker-host-delete-${id}`)}
                </div>
              );
            })}
            {!hosts.length && !loadError && <p className="muted">No worker hosts registered.</p>}
          </div>
        </>
      )}

      {mode === "manage" && (
        <>
          {issuedToken && (
            <div className="card">
              <h2>Worker host token</h2>
              <p className="error">This token is shown once — copy now.</p>
              <p className="muted">{issuedToken.label} · {issuedToken.hostId}</p>
              <code ref={tokenCodeRef}>{issuedToken.token}</code>
              <div className="actions">
                <button
                  className="primary"
                  type="button"
                  onClick={() => void copyIssuedToken()}
                >
                  Copy
                </button>
                <button type="button" onClick={() => setIssuedToken(null)}>Dismiss</button>
              </div>
              {status("worker-host-token-copy")}
            </div>
          )}

          {canPause ? (
            <form className="card" onSubmit={createHost}>
              <h2>Create worker host</h2>
              <label htmlFor="worker-host-label">Label</label>
              <input
                id="worker-host-label"
                type="text"
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                required
              />
              <label htmlFor="worker-host-base-url">HTTPS base URL</label>
              <input
                id="worker-host-base-url"
                type="url"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="https://worker.example"
                required
              />
              <div className="actions">
                <button className="primary" type="submit">Create worker host</button>
              </div>
              {status("worker-host-create")}
            </form>
          ) : scopeNotice("create, enable, disable, or delete worker hosts", "company.pause")}
        </>
      )}
    </section>
  );
}
