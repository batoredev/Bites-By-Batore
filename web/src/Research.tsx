import { useEffect, useState, type FormEvent } from "react";
import { api, post, safeLink, dateText } from "./api";
import { ErrorBox } from "./components";
import type { Venue, Category } from "./types";
import { AgentControls, CorrectionEditor } from "./ResearchLearning";

type Source = {
  id: string;
  url: string;
  platform: string;
  state: string;
  creator: string;
  analysis: Record<string, unknown>;
  content: Record<string, unknown>;
};
type Case = {
  id: string;
  query: string;
  state: string;
  created_at: string;
  result: Record<string, unknown>;
  tasks: {
    role: string;
    state: string;
    result: Record<string, unknown>;
    error: string;
  }[];
  sources: Source[];
};

function taskLabel(task: Case["tasks"][number]) {
  if (task.state !== "done") return task.state;
  const gaps = Array.isArray(task.result.gaps) && task.result.gaps.length > 0;
  if (task.result.unavailable || (gaps && task.result.analyzed_sources === 0))
    return "Evidence unavailable";
  if (gaps || (task.role === "discovery" && task.result.source_count === 0))
    return "Completed with gaps";
  return "Completed";
}

function Evidence({ value }: { value: unknown }) {
  if (value == null || value === "")
    return <span className="muted">Unknown</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ul>
        {value.map((v, i) => (
          <li key={i}>
            <Evidence value={v} />
          </li>
        ))}
      </ul>
    ) : (
      <span className="muted">None recorded</span>
    );
  if (typeof value === "object")
    return (
      <dl className="research-evidence">
        {Object.entries(value).map(([key, v]) => (
          <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt>
            <dd>
              <Evidence value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return (
    <span>
      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
    </span>
  );
}

function ConcludeCase({ item, refresh }: { item: Case; refresh: () => void }) {
  const [decision, setDecision] = useState("insufficient_evidence"),
    [reason, setReason] = useState(""),
    [error, setError] = useState("");
  return (
    <details>
      <summary>Conclude the human review</summary>
      <form
        className="stack-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          try {
            await post(`/admin/investigations/${item.id}/conclude`, {
              decision,
              reason,
            });
            refresh();
          } catch (err) {
            setError((err as Error).message);
          }
        }}
      >
        <p className="small-text">
          A conclusion does not accept unverified facts. Supported venues must
          already have independent branch confirmation and current essential
          evidence.
        </p>
        <label>
          Conclusion
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
          >
            <option value="insufficient_evidence">
              Insufficient evidence to recommend
            </option>
            <option value="use_verified_venues">
              Use independently verified venues, retain limitations
            </option>
          </select>
        </label>
        <label>
          Review findings
          <textarea
            required
            minLength={20}
            maxLength={1500}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button className="secondary">Record investigation conclusion</button>
        <ErrorBox message={error} />
      </form>
    </details>
  );
}

function ResolveSource({
  source,
  venues,
  refresh,
}: {
  source: Source;
  venues: Venue[];
  refresh: () => void;
}) {
  const [venueId, setVenueId] = useState("");
  const [reason, setReason] = useState("");
  const [evidence, setEvidence] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({
    name: "",
    area: "",
    address: "",
    lat: "",
    lng: "",
    category: "food" as Category,
  });
  async function resolve(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(`/admin/research-sources/${source.id}/resolve`, {
        venue_id: venueId === "new" ? "" : venueId,
        venue:
          venueId === "new"
            ? {
                ...draft,
                lat: Number(draft.lat),
                lng: Number(draft.lng),
                tags: [],
                details: {},
              }
            : null,
        reason,
        evidence_url: evidence,
      });
      refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details>
      <summary>Confirm the exact branch</summary>
      <form className="stack-form" onSubmit={resolve}>
        <p className="small-text">
          Use independent branch evidence. New venues remain pending until
          essential current facts are accepted in the venue desk.
        </p>
        <label>
          Venue
          <select
            required
            value={venueId}
            onChange={(e) => setVenueId(e.target.value)}
          >
            <option value="">Choose a venue</option>
            {venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} · {v.area}
              </option>
            ))}
            <option value="new">Create a pending venue</option>
          </select>
        </label>
        {(["caption", "video"] as const).flatMap((role) => {
          const analysis = source.analysis[role] as
            | { venue_candidates?: { name: string; address_clues: string[] }[] }
            | undefined;
          return (analysis?.venue_candidates || []).map((candidate, index) => (
            <button
              className="text-button"
              type="button"
              key={`${role}-${index}`}
              onClick={() => {
                setVenueId("new");
                setDraft({
                  ...draft,
                  name: candidate.name,
                  address: candidate.address_clues.join(", "),
                });
              }}
            >
              Use extracted candidate: {candidate.name}
            </button>
          ));
        })}
        {venueId === "new" && (
          <>
            <div className="two-col">
              {(["name", "area", "address"] as const).map((key) => (
                <label key={key}>
                  {key}
                  <input
                    required
                    minLength={key === "address" ? 5 : 2}
                    value={draft[key]}
                    onChange={(e) =>
                      setDraft({ ...draft, [key]: e.target.value })
                    }
                  />
                </label>
              ))}
              <label>
                Category
                <select
                  value={draft.category}
                  onChange={(e) =>
                    setDraft({ ...draft, category: e.target.value as Category })
                  }
                >
                  {[
                    "food",
                    "cafe",
                    "park",
                    "cinema",
                    "gaming",
                    "bowling",
                    "adventure",
                  ].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              {(["lat", "lng"] as const).map((key) => (
                <label key={key}>
                  {key === "lat" ? "Confirmed latitude" : "Confirmed longitude"}
                  <input
                    required
                    type="number"
                    step="any"
                    min={key === "lat" ? -90 : -180}
                    max={key === "lat" ? 90 : 180}
                    value={draft[key]}
                    onChange={(e) =>
                      setDraft({ ...draft, [key]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
          </>
        )}
        <label>
          Independent evidence link
          <input
            required
            type="url"
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            placeholder="https://…"
          />
        </label>
        <label>
          Why this is the exact branch
          <textarea
            required
            minLength={15}
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <ErrorBox message={error} />
        <button className="secondary" disabled={busy || !venueId}>
          {busy ? "Recording…" : "Record branch confirmation"}
        </button>
      </form>
    </details>
  );
}

function AssessSource({ source }: { source: Source }) {
  const [outcome, setOutcome] = useState("supported"),
    [reason, setReason] = useState(""),
    [url, setUrl] = useState("");
  const [message, setMessage] = useState(""),
    [error, setError] = useState("");
  if (!source.creator)
    return (
      <p className="small-text muted">
        Creator history cannot be assessed until a source identity is available.
      </p>
    );
  return (
    <details>
      <summary>Record a factual source outcome</summary>
      <form
        className="stack-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          try {
            await post(`/admin/research-sources/${source.id}/assess`, {
              outcome,
              reason,
              evidence_url: url,
            });
            setMessage(
              "Outcome recorded. Repeated evidence origins do not increase the sample size.",
            );
          } catch (err) {
            setError((err as Error).message);
          }
        }}
      >
        <p className="small-text">
          Evaluate factual accuracy using independent evidence. Personal taste
          and likes are not factual accuracy. Use “outdated” when a once-correct
          fact changed.
        </p>
        <label>
          Outcome
          <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {["supported", "refuted", "outdated", "unresolved"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Corroborating evidence
          <input
            required
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>
        <label>
          What was checked?
          <textarea
            required
            minLength={15}
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button className="secondary">Record factual outcome</button>
        <ErrorBox message={error} />
        {message && <p role="status">{message}</p>}
      </form>
    </details>
  );
}

export default function Research({
  admin = false,
  venues = [],
}: {
  admin?: boolean;
  venues?: Venue[];
}) {
  const [cases, setCases] = useState<Case[]>([]),
    [query, setQuery] = useState(""),
    [url, setUrl] = useState("");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [open, setOpen] = useState("");
  const load = () =>
    api<Case[]>(admin ? "/admin/investigations" : "/investigations")
      .then(setCases)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, [admin]);
  async function start(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const c = await post<Case>("/investigations", { query, url });
      setOpen(c.id);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(path: string) {
    try {
      await post(path);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <section className="research-section">
      <div className="section-heading">
        <div>
          <div className="eyebrow">FOLLOW THE EVIDENCE</div>
          <h2>
            {admin ? "Investigation review" : "Find something worth going for."}
          </h2>
        </div>
        <button type="button" className="secondary" onClick={load}>
          Refresh investigations
        </button>
      </div>
      {!admin && (
        <form className="panel stack-form" onSubmit={start}>
          <p>
            Start with a cuisine, activity or reel. Follow discovery, analysis
            and branch checks as they progress. Unverified finds stay separate
            from recommendations.
          </p>
          <div className="two-col">
            <label>
              What should we investigate?
              <input
                required
                minLength={2}
                maxLength={500}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Coimbatore sushi"
              />
            </label>
            <label>
              Reel or YouTube link <small>Optional</small>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                maxLength={2000}
              />
            </label>
          </div>
          <button className="primary" disabled={busy}>
            {busy ? "Starting…" : "Start investigation"}
          </button>
        </form>
      )}
      {admin && <AgentControls refresh={load} />}
      <ErrorBox message={error} />
      <div className="submission-list">
        {cases.map((c) => (
          <article className="panel" key={c.id}>
            <div className="submission-head">
              <button
                type="button"
                className="text-button"
                aria-expanded={open === c.id}
                onClick={() => setOpen(open === c.id ? "" : c.id)}
              >
                <strong>{c.query}</strong>
                <span className="status">{c.state}</span>
              </button>
              <small>{dateText(c.created_at)}</small>
            </div>
            {open === c.id && (
              <div className="analysis-result">
                <ol className="research-tasks">
                  {c.tasks.map((t) => (
                    <li key={t.role}>
                      <strong>{t.role}</strong>
                      <span>{taskLabel(t)}</span>
                      {t.error && <ErrorBox message={t.error} />}
                      <details>
                        <summary>Evidence and limitations</summary>
                        <Evidence value={t.result} />
                      </details>
                    </li>
                  ))}
                </ol>
                {c.sources.map((s) => (
                  <div className="research-source" key={s.id}>
                    <h3>
                      {s.creator || s.platform} · {s.state}
                    </h3>
                    <p className="small-text">
                      {(["caption", "comments", "video"] as const)
                        .map((role) => {
                          const result = s.analysis[role] as
                            { status?: string } | undefined;
                          return `${role}: ${result?.status === "observations_only" ? "analysed, needs review" : result?.status === "unavailable" ? "unavailable" : "pending"}`;
                        })
                        .join(" · ")}
                    </p>
                    {safeLink(s.url) && (
                      <a
                        href={safeLink(s.url)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original source
                      </a>
                    )}
                    <details>
                      <summary>Collected source and search preview</summary>
                      <p className="small-text">
                        Search previews are leads. They do not establish that
                        the full reel, caption or comments were retrieved.
                      </p>
                      <Evidence value={s.content} />
                    </details>
                    <details>
                      <summary>Read observations and branch candidates</summary>
                      <Evidence value={s.analysis} />
                    </details>
                    {admin &&
                      ["review", "complete", "unavailable"].includes(
                        c.state,
                      ) && (
                        <ResolveSource
                          source={s}
                          venues={venues}
                          refresh={load}
                        />
                      )}
                    {admin && <AssessSource source={s} />}
                    {admin && <CorrectionEditor sourceId={s.id} />}
                  </div>
                ))}
                <details>
                  <summary>Review outcome and remaining evidence</summary>
                  <Evidence value={c.result} />
                </details>
                {admin &&
                  [
                    "review",
                    "complete",
                    "unavailable",
                    "complete_with_limits",
                    "insufficient_evidence",
                  ].includes(c.state) && (
                    <ConcludeCase item={c} refresh={load} />
                  )}
                <div className="mood-row">
                  {!admin && ["queued", "running"].includes(c.state) && (
                    <button
                      className="secondary"
                      onClick={() => action(`/investigations/${c.id}/cancel`)}
                    >
                      Cancel investigation
                    </button>
                  )}
                  {!admin && c.state === "failed" && (
                    <button
                      className="secondary"
                      onClick={() => action(`/investigations/${c.id}/retry`)}
                    >
                      Resume failed step
                    </button>
                  )}
                  {admin &&
                    ["review", "complete", "unavailable"].includes(c.state) && (
                      <button
                        className="secondary"
                        onClick={() =>
                          action(`/admin/investigations/${c.id}/recheck`)
                        }
                      >
                        Recheck accepted venue facts
                      </button>
                    )}
                </div>
              </div>
            )}
          </article>
        ))}
      </div>
      {!cases.length && (
        <p className="muted">
          No investigations yet. Starting one does not automatically publish a
          venue.
        </p>
      )}
    </section>
  );
}
