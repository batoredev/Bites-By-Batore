import { useEffect, useState, type FormEvent } from "react";
import { api, post } from "./api";
import { ErrorBox } from "./components";

type Alert = {
  id: string;
  kind: string;
  url: string;
  detail: unknown;
  at: string;
};
type Packet = {
  id: string;
  name: string;
  area: string;
  category: string;
  status: string;
  maps_url: string;
  blockers: string[];
  missing: string[];
  alerts: Alert[];
  ready_for_final_approval: boolean;
  location_approved: boolean;
  sources: { url: string; type: string; collected_at?: string }[];
  page_checks: Record<
    string,
    {
      state: string;
      checked_at: string;
      next_check_at: string;
      observed_fields?: unknown;
      previous_values?: unknown;
      error?: string;
    }
  >;
  fact_evidence: unknown[];
  conflicts: unknown[];
  possible_duplicates: string[];
};
type Report = {
  draft_count: number;
  approved_count: number;
  ready_for_approval: number;
  open_alerts: number;
  pages_monitored: number;
  pages_overdue: number;
  unavailable_pages: number;
  coverage: string;
  cadence: {
    page_hours: number;
    reel_days: number;
    reel_checks_per_day: number;
    note: string;
  };
  packets: Packet[];
  failed_jobs: { id: string; kind: string; error: string }[];
  grid: { area: string; category: string; drafts: number; approved: number }[];
  evaluation_queue: {
    id: string;
    url: string;
    languages: string[];
    labels: string[];
    raw_available: boolean;
    watch: unknown;
  }[];
};

function AlertReview({
  item,
  spotId,
  reload,
}: {
  item: Alert;
  spotId: string;
  reload: () => void;
}) {
  const [reason, setReason] = useState(""),
    [url, setUrl] = useState(item.url);
  const [checked, setChecked] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(
        `/admin/maintenance/packets/${spotId}/alerts/${item.id}/resolve`,
        {
          checked_original: checked,
          evidence_url: url,
          reason,
        },
      );
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>
        {item.kind.replaceAll("_", " ")} · {new Date(item.at).toLocaleString()}
      </summary>
      <pre>{JSON.stringify(item.detail, null, 2)}</pre>
      <form className="stack-form" onSubmit={submit}>
        <label>
          Checked evidence URL
          <input
            type="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <label>
          What changed and how was it checked?
          <textarea
            required
            minLength={20}
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <label>
          <input
            type="checkbox"
            required
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          I inspected the source and reviewed the affected facts.
        </label>
        <p>
          Resolving this alert does not accept facts or approve this location.
        </p>
        <ErrorBox message={error} />
        <button className="secondary" disabled={busy}>
          Record alert review
        </button>
      </form>
    </details>
  );
}

export default function Maintenance() {
  const [data, setData] = useState<Report | null>(null),
    [error, setError] = useState("");
  const [selected, setSelected] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api<Report>("/admin/maintenance")
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  const packet = data?.packets.find((p) => p.id === selected);
  return (
    <section className="panel">
      <h2>Inventory checks and approval packets</h2>
      <p>
        Inspect changes, evidence gaps and each location's approval
        requirements. The agent cannot approve a location for you.
      </p>
      <ErrorBox message={error} />
      {message && <p role="status">{message}</p>}
      {data && (
        <>
          <p>
            {data.draft_count} active records · {data.approved_count} approved ·{" "}
            {data.ready_for_approval} ready for final approval.
          </p>
          <p>
            {data.pages_monitored} monitored page records · {data.pages_overdue}{" "}
            checks overdue · {data.unavailable_pages} unavailable ·{" "}
            {data.open_alerts} open alerts.
          </p>
          <p>{data.coverage}</p>
          <p>
            Page checks: every {data.cadence.page_hours} hours. Existing reel
            checks: every {data.cadence.reel_days} days, up to{" "}
            {data.cadence.reel_checks_per_day} scheduled per day.{" "}
            {data.cadence.note}
          </p>
          <div className="actions">
            <button
              className="secondary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const result = await post<{ queued: number }>(
                    "/admin/maintenance/schedule",
                  );
                  setMessage(
                    `${result.queued} due source checks queued. No locations approved.`,
                  );
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Queue due source checks
            </button>
            <button className="secondary" onClick={() => void load()}>
              Refresh inventory checks
            </button>
          </div>
          <details>
            <summary>Area and category coverage</summary>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Area</th>
                    <th>Category</th>
                    <th>Drafts</th>
                    <th>Approved</th>
                  </tr>
                </thead>
                <tbody>
                  {data.grid.map((c) => (
                    <tr key={`${c.area}-${c.category}`}>
                      <td>{c.area}</td>
                      <td>{c.category}</td>
                      <td>{c.drafts}</td>
                      <td>{c.approved}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <label>
            Location approval packet
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">Choose a location to inspect</option>
              {data.packets.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name} · {p.area || "Area unknown"} · {p.blockers.length}{" "}
                  blockers
                </option>
              ))}
            </select>
          </label>
          {packet && (
            <article>
              <h3>{packet.name}</h3>
              <p>
                {packet.ready_for_final_approval
                  ? "Ready for your final review in Venue desk"
                  : "Evidence or review work remains"}
              </p>
              <a href={packet.maps_url} target="_blank" rel="noreferrer">
                Inspect Maps identity
              </a>
              <ul>
                {packet.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <p>
                Missing draft information:{" "}
                {packet.missing.join(", ") ||
                  "None detected; this is not verification"}
              </p>
              {!!packet.possible_duplicates.length && (
                <p>
                  Possible duplicates need branch review:{" "}
                  {packet.possible_duplicates.length}
                </p>
              )}
              {!!packet.conflicts.length && (
                <details>
                  <summary>Conflicting draft values</summary>
                  <pre>{JSON.stringify(packet.conflicts, null, 2)}</pre>
                </details>
              )}
              <details>
                <summary>Source links and fetch dates</summary>
                <ul>
                  {packet.sources.map((s, i) => (
                    <li key={i}>
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.type}: {s.url}
                      </a>{" "}
                      · {s.collected_at || "Date unknown"}
                    </li>
                  ))}
                </ul>
              </details>
              {Object.entries(packet.page_checks).map(([url, p]) => (
                <details key={url}>
                  <summary>
                    {p.state.replaceAll("_", " ")}: {url}
                  </summary>
                  <p>
                    Checked {p.checked_at}. Next target {p.next_check_at}. Page
                    observations are unverified.
                  </p>
                  {p.error && <p>{p.error}</p>}
                  <pre>
                    {JSON.stringify(
                      {
                        observed: p.observed_fields,
                        previous: p.previous_values,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </details>
              ))}
              {packet.alerts.map((a) => (
                <AlertReview
                  key={`${packet.id}-${a.id}`}
                  item={a}
                  spotId={packet.id}
                  reload={() => void load()}
                />
              ))}
              <details>
                <summary>Accepted and pending fact evidence</summary>
                <pre>{JSON.stringify(packet.fact_evidence, null, 2)}</pre>
              </details>
              <p>
                Use Identified spots to prepare the exact branch, then Venue
                desk to review essential facts and approve this location.
              </p>
            </article>
          )}
          <details>
            <summary>
              Agent-discovered evaluation examples (
              {data.evaluation_queue.length})
            </summary>
            <ul>
              {data.evaluation_queue.map((s) => (
                <li key={s.id}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.url}
                  </a>{" "}
                  · detected languages: {s.languages.join(", ") || "unknown"} ·{" "}
                  {s.labels.length} reviewed tasks ·{" "}
                  {s.raw_available
                    ? "source text available"
                    : "source text expired or unavailable"}
                </li>
              ))}
            </ul>
            <p>
              Use Instagram accuracy review below to label independently checked
              examples. Detected languages are model observations.
            </p>
          </details>
          {!!data.failed_jobs.length && (
            <details>
              <summary>
                Failed maintenance jobs ({data.failed_jobs.length})
              </summary>
              <ul>
                {data.failed_jobs.map((j) => (
                  <li key={j.id}>
                    {j.kind}: {j.error}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
