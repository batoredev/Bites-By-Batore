import { useEffect, useState } from "react";
import { api, post } from "./api";
import { ErrorBox } from "./components";

type Correction = {
  id: string;
  source_id: string;
  scope: string;
  corrected: string;
  active: boolean;
};
export function CorrectionEditor({ sourceId }: { sourceId: string }) {
  const [rows, setRows] = useState<Correction[]>([]);
  const [role, setRole] = useState("caption"),
    [scope, setScope] = useState("");
  const [original, setOriginal] = useState(""),
    [corrected, setCorrected] = useState(""),
    [reason, setReason] = useState("");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<Correction[]>("/admin/research-corrections")
      .then((r) => setRows(r.filter((x) => x.source_id === sourceId)))
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, [sourceId]);
  return (
    <details>
      <summary>Teach the agent a correction</summary>
      <p className="small-text">
        Your correction is reused when later evidence contains the same scope
        phrase. It does not publish venue facts or train model weights.
      </p>
      <form
        className="stack-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await post(`/admin/research-sources/${sourceId}/corrections`, {
              role,
              scope,
              original,
              corrected,
              reason,
            });
            await load();
            setOriginal("");
            setCorrected("");
            setReason("");
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Specialist
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="caption">Caption / description</option>
            <option value="comments">Comments</option>
            <option value="video">Video</option>
          </select>
        </label>
        <label>
          Scope phrase
          <input
            required
            minLength={3}
            maxLength={120}
            placeholder="Exact venue name or relevant phrase"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          />
        </label>
        <label>
          What did the agent get wrong?
          <textarea
            required
            minLength={2}
            maxLength={1000}
            value={original}
            onChange={(e) => setOriginal(e.target.value)}
          />
        </label>
        <label>
          Correct interpretation
          <textarea
            required
            minLength={2}
            maxLength={1000}
            value={corrected}
            onChange={(e) => setCorrected(e.target.value)}
          />
        </label>
        <label>
          Evidence and reason
          <textarea
            required
            minLength={15}
            maxLength={1000}
            placeholder="Explain the source text, sign or timestamp that supports your correction"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button className="secondary" disabled={busy}>
          {busy ? "Saving…" : "Save learning example"}
        </button>
      </form>
      <ErrorBox message={error} />
      <ul>
        {rows.map((r) => (
          <li key={r.id}>
            <strong>{r.scope}</strong>: {r.corrected}{" "}
            {r.active ? (
              <button
                className="text-button"
                onClick={async () => {
                  try {
                    await api(`/admin/research-corrections/${r.id}`, {
                      method: "DELETE",
                    });
                    await load();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Stop reusing this correction
              </button>
            ) : (
              <span>Revoked</span>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}

type Runtime = {
  mode: string;
  model: string;
  model_installed: boolean;
  runtime_error: string;
  paused: boolean;
  autonomous: boolean;
  daily_case_limit: number;
  public_search: boolean;
  direct_browser: boolean;
  source_limit: number;
  browser_daily_limit: number;
  instagram_connector: string;
};
export function AgentControls({ refresh }: { refresh: () => void }) {
  const [state, setState] = useState<Runtime | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<Runtime>("/admin/research-runtime")
      .then(setState)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);
  if (!state || state.mode === "demo") return null;
  return (
    <div className="panel stack-form">
      <h3>Coimbatore research agent</h3>
      <p>
        No example links needed. The agent rotates through food and
        entertainment topics and neighbourhoods, then brings its findings here
        for review.
      </p>
      <p className="small-text">
        {state.mode === "local"
          ? `Local model: ${state.model} · ${state.model_installed ? "installed" : "unavailable"}. `
          : "Hosted analysis configured separately. "}
        {state.paused
          ? "New discovery paused."
          : state.autonomous
            ? "Automatic discovery enabled while this computer and worker are running."
            : "Automatic discovery disabled."}{" "}
        Up to {state.daily_case_limit} automatic investigations per day.
      </p>
      <p className="small-text">
        Public search: {state.public_search ? "enabled" : "disabled"}. Direct
        browser: {state.direct_browser ? "enabled" : "disabled"}. Optional API
        connector: {state.instagram_connector}. Captions, comments and video may
        have different access limits. Newest dated sources are processed first.
        All discovered relevant sources stay queued; {state.source_limit} is the
        processing batch size, not the investigation total.
      </p>
      <div className="mood-row">
        <button
          className="primary"
          disabled={busy || state.paused}
          onClick={async () => {
            setBusy(true);
            setError("");
            try {
              await post("/admin/research-next");
              refresh();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Find the next examples for me
        </button>
        <button
          className="secondary"
          onClick={async () => {
            try {
              await post("/admin/research-control", { paused: !state.paused });
              await load();
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          {state.paused ? "Resume discovery" : "Pause new discovery"}
        </button>
      </div>
      <ErrorBox message={error || state.runtime_error} />
    </div>
  );
}
