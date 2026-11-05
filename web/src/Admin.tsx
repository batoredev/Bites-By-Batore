import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowsClockwise,
  Play,
  Plus,
  CheckCircle,
  XCircle,
} from "@phosphor-icons/react";
import { api, post, dateText } from "./api";
import {
  PageTitle,
  ErrorBox,
  Loading,
  Empty,
  Modal,
  categories,
} from "./components";
import type { AdminData, Claim, Venue } from "./types";
import Research from "./Research";
import Quality from "./Quality";
import IdentifiedSpots from "./IdentifiedSpots";

function OperationsEditor({
  venue,
  onClose,
  onSaved,
}: {
  venue: Venue;
  onClose: () => void;
  onSaved: () => void;
}) {
  const d = venue.details;
  const [form, setForm] = useState({
    visit_minutes: Number(d.visit_minutes || 60),
    wait_minutes: Number(d.wait_minutes || 0),
    fee_per_group: Number(d.fee_per_group || 0),
    max_group: Number(d.max_group || 6),
    child_friendly: !!d.child_friendly,
    min_age: Number(d.min_age || 0),
    sessions: Array.isArray(d.sessions) ? d.sessions.join(", ") : "",
    google_place_id: d.google_place_id || "",
    booking_url: d.booking_url || "",
    description: d.description || "",
    speciality: d.speciality || "",
    branch_confirmed: !!d.branch_confirmed,
    packages: JSON.stringify(d.packages || [], null, 2),
    dated_sessions: JSON.stringify(d.dated_sessions || [], null, 2),
  });
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api(`/admin/venues/${venue.id}/operations`, {
        method: "PUT",
        body: JSON.stringify({
          ...form,
          packages: JSON.parse(form.packages),
          dated_sessions: JSON.parse(form.dated_sessions),
          sessions: form.sessions
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean),
        }),
      });
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={`Planning details · ${venue.name}`} onClose={onClose}>
      <form className="stack-form" onSubmit={save}>
        <p className="muted">
          Use independently confirmed operational details. These changes
          invalidate existing saved plans.
        </p>
        <div className="two-col">
          {(
            [
              {
                key: "visit_minutes",
                label: "Visit duration (minutes)",
                min: 5,
                max: 480,
              },
              {
                key: "wait_minutes",
                label: "Waiting / check-in (minutes)",
                min: 0,
                max: 180,
              },
              {
                key: "fee_per_group",
                label: "Fees per group (INR)",
                min: 0,
                max: 10000,
              },
              {
                key: "max_group",
                label: "Confirmed group capacity",
                min: 1,
                max: 100,
              },
              { key: "min_age", label: "Minimum age", min: 0, max: 21 },
            ] as const
          ).map((x) => (
            <label key={x.key}>
              {x.label}
              <input
                required
                type="number"
                min={x.min}
                max={x.max}
                value={form[x.key]}
                onChange={(e) => setForm({ ...form, [x.key]: +e.target.value })}
              />
            </label>
          ))}
        </div>
        <label>
          Screening times · India time
          <input
            value={form.sessions}
            placeholder="11:00, 14:30, 18:00"
            onChange={(e) => setForm({ ...form, sessions: e.target.value })}
          />
        </label>
        <label>
          Exact Google place ID
          <input
            value={form.google_place_id}
            onChange={(e) =>
              setForm({ ...form, google_place_id: e.target.value })
            }
          />
        </label>
        <label>
          External booking link
          <input
            type="url"
            value={form.booking_url}
            onChange={(e) => setForm({ ...form, booking_url: e.target.value })}
          />
        </label>
        <label>
          Dish or activity
          <input
            value={form.speciality}
            onChange={(e) => setForm({ ...form, speciality: e.target.value })}
          />
        </label>
        <label>
          Description
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </label>
        <div className="checks vertical">
          <label>
            <input
              type="checkbox"
              checked={form.child_friendly}
              onChange={(e) =>
                setForm({ ...form, child_friendly: e.target.checked })
              }
            />
            Confirmed child friendly
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.branch_confirmed}
              onChange={(e) =>
                setForm({ ...form, branch_confirmed: e.target.checked })
              }
            />
            Exact branch identity independently confirmed
          </label>
        </div>
        <details>
          <summary>Confirmed package and dated-session feeds</summary>
          <p className="small-text">
            Use partner records with an HTTPS source and timezone-aware expiry.
            Prices are INR. These records can also arrive through the signed
            merchant feed.
          </p>
          <label>
            Activity packages (JSON)
            <textarea
              value={form.packages}
              onChange={(e) => setForm({ ...form, packages: e.target.value })}
              placeholder='[{"name":"One game","unit":"person","price":300,"duration_minutes":30,"expires_at":"2026-11-05T18:00:00+05:30","source_url":"https://venue.example/menu"}]'
            />
          </label>
          <label>
            Dated sessions (JSON)
            <textarea
              value={form.dated_sessions}
              onChange={(e) =>
                setForm({ ...form, dated_sessions: e.target.value })
              }
              placeholder='[{"name":"Screening","starts_at":"2026-11-05T18:00:00+05:30","duration_minutes":120,"price_per_person":250,"available_places":10,"expires_at":"2026-11-05T17:00:00+05:30","source_url":"https://venue.example/session"}]'
            />
          </label>
        </details>
        <ErrorBox message={error} />
        <button className="primary" disabled={busy}>
          Save operational details
        </button>
      </form>
    </Modal>
  );
}

export default function Admin({ onChanged }: { onChanged: () => void }) {
  const [data, setData] = useState<AdminData | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [tab, setTab] = useState("review"),
    [reasons, setReasons] = useState<Record<string, string>>({}),
    [query, setQuery] = useState("Coimbatore sushi cafes entertainment");
  const [newVenue, setNewVenue] = useState({
    name: "",
    category: "food",
    area: "",
    address: "",
    lat: 11.0168,
    lng: 76.9558,
    tags: "",
    google_place_id: "",
    speciality: "",
  });
  const [fact, setFact] = useState({
    venue_id: "",
    field: "price_per_person",
    value: "",
    source_url: "",
    source_type: "merchant",
    source_group: "",
    hours: "",
  });
  const [expandedJob, setExpandedJob] = useState("");
  const [editing, setEditing] = useState<Venue | null>(null);
  const load = () =>
    api<AdminData>("/admin/overview")
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
    const timer = setInterval(load, 20000);
    return () => clearInterval(timer);
  }, []);
  async function action(path: string, body: unknown = {}) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await post(path, body);
      await load();
      onChanged();
      setMessage("Action completed. The queue and records are up to date.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function review(c: Claim, decision: string) {
    if ((reasons[c.id] || "").trim().length < 5) {
      setError("Add a review reason of at least five characters.");
      return;
    }
    await action(`/admin/claims/${c.id}/review`, {
      decision,
      reason: reasons[c.id],
    });
  }
  async function createVenue(e: FormEvent) {
    e.preventDefault();
    await action("/admin/venues", {
      ...newVenue,
      tags: newVenue.tags
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      details: {
        google_place_id: newVenue.google_place_id,
        speciality: newVenue.speciality,
      },
    });
  }
  async function addFact(e: FormEvent) {
    e.preventDefault();
    let value: unknown = fact.value;
    try {
      if (fact.field === "price_per_person") value = Number(value);
      else if (
        ["closed", "vegetarian", "wheelchair", "hours"].includes(fact.field)
      )
        value = JSON.parse(fact.value);
    } catch {
      setError("Use valid JSON for hours or true/false for a yes/no fact.");
      return;
    }
    await action("/corrections", {
      venue_id: fact.venue_id,
      field: fact.field,
      value: { value },
      source_url: fact.source_url,
      source_type: fact.source_type,
      source_group: fact.source_group,
      observed_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 86400000).toISOString(),
    });
  }
  if (!data)
    return (
      <>
        <ErrorBox message={error} />
        <Loading label="Reading the operations dashboard…" />
      </>
    );
  return (
    <>
      <PageTitle
        eyebrow="BATORE OPERATIONS"
        title="Keep the knowledge honest."
        description="Review unusual changes, inspect freshness and keep discovery moving."
        action={
          <button className="secondary" onClick={load}>
            <ArrowsClockwise />
            Refresh view
          </button>
        }
      />
      <div className="admin-stats">
        <div>
          <strong>
            {data.venues.filter((v) => v.status === "published").length}
          </strong>
          <span>Published places</span>
        </div>
        <div>
          <strong>{data.review.length}</strong>
          <span>Facts awaiting review</span>
        </div>
        <div>
          <strong>{data.expired_claims}</strong>
          <span>Expired accepted facts</span>
        </div>
        <div>
          <strong>
            {data.jobs.filter((j) => j.state === "failed").length}
          </strong>
          <span>Failed jobs</span>
        </div>
      </div>
      {data.mode === "demo" && (
        <div className="notice">
          Local demo operations. All visitors on this computer can explore the
          demo admin. Live mode requires server-authorized administrator IDs.
        </div>
      )}
      <div className="tabs admin-tabs">
        {[
          "review",
          "research",
          "spots",
          "quality",
          "venues",
          "jobs",
          "integrations",
          "audit",
        ].map((t) => (
          <button
            key={t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t === "review"
              ? "Review queue"
              : t === "research"
                ? "Investigations"
                : t === "spots"
                  ? "Identified spots"
                  : t === "quality"
                    ? "Data readiness"
                    : t === "venues"
                      ? "Venue desk"
                      : t === "jobs"
                        ? "Background work"
                        : t === "integrations"
                          ? "Integrations"
                          : "Audit trail"}
          </button>
        ))}
      </div>
      <ErrorBox message={error} />
      {tab === "research" && <Research admin venues={data.venues} />}
      {tab === "spots" && <IdentifiedSpots onChanged={load} />}
      {tab === "quality" && <Quality />}
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
      {tab === "review" &&
        (data.review.length ? (
          <div className="review-grid">
            {data.review.map((c) => (
              <article className="panel" key={c.id}>
                <div className="eyebrow">{c.field.replaceAll("_", " ")}</div>
                <h3>
                  {data.venues.find((v) => v.id === c.venue_id)?.name ||
                    c.venue_id}
                </h3>
                <p className="review-value">
                  Proposed: {JSON.stringify(c.value.value)}
                </p>
                <p>{c.reason}</p>
                <p className="small-text muted">
                  Source type: {c.source_type} · Observed{" "}
                  {dateText(c.observed_at)}
                  <br />
                  Expires {dateText(c.expires_at)}
                </p>
                <label>
                  Review reason
                  <input
                    value={reasons[c.id] || ""}
                    onChange={(e) =>
                      setReasons({ ...reasons, [c.id]: e.target.value })
                    }
                    placeholder="What evidence supports this decision?"
                  />
                </label>
                <div className="inline-actions">
                  <button
                    disabled={busy}
                    className="primary"
                    onClick={() => review(c, "approve")}
                  >
                    <CheckCircle />
                    Approve
                  </button>
                  <button
                    disabled={busy}
                    className="secondary"
                    onClick={() => review(c, "reject")}
                  >
                    <XCircle />
                    Reject
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty title="No unresolved changes">
            Unusual prices, closures, access changes and unverified reports
            appear here.
          </Empty>
        ))}
      {tab === "venues" && (
        <>
          <div className="coverage-strip">
            {Object.entries(data.coverage).map(([k, n]) => (
              <span key={k}>
                {k} <strong>{n}</strong>
              </span>
            ))}
          </div>
          <div className="two-col admin-forms">
            <form className="panel stack-form" onSubmit={createVenue}>
              <h3>Add a venue for verification</h3>
              <label>
                Name
                <input
                  required
                  value={newVenue.name}
                  onChange={(e) =>
                    setNewVenue({ ...newVenue, name: e.target.value })
                  }
                />
              </label>
              <div className="two-col">
                <label>
                  Category
                  <select
                    value={newVenue.category}
                    onChange={(e) =>
                      setNewVenue({ ...newVenue, category: e.target.value })
                    }
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Neighbourhood
                  <input
                    required
                    value={newVenue.area}
                    onChange={(e) =>
                      setNewVenue({ ...newVenue, area: e.target.value })
                    }
                  />
                </label>
              </div>
              <label>
                Independently sourced address
                <input
                  required
                  value={newVenue.address}
                  onChange={(e) =>
                    setNewVenue({ ...newVenue, address: e.target.value })
                  }
                />
              </label>
              <div className="two-col">
                <label>
                  Latitude
                  <input
                    type="number"
                    step="any"
                    required
                    value={newVenue.lat}
                    onChange={(e) =>
                      setNewVenue({ ...newVenue, lat: +e.target.value })
                    }
                  />
                </label>
                <label>
                  Longitude
                  <input
                    type="number"
                    step="any"
                    required
                    value={newVenue.lng}
                    onChange={(e) =>
                      setNewVenue({ ...newVenue, lng: +e.target.value })
                    }
                  />
                </label>
              </div>
              <label>
                Tags, separated by commas
                <input
                  value={newVenue.tags}
                  onChange={(e) =>
                    setNewVenue({ ...newVenue, tags: e.target.value })
                  }
                />
              </label>
              <label>
                Dish or activity
                <input
                  value={newVenue.speciality}
                  onChange={(e) =>
                    setNewVenue({ ...newVenue, speciality: e.target.value })
                  }
                />
              </label>
              <label>
                Exact Google place ID
                <input
                  value={newVenue.google_place_id}
                  onChange={(e) =>
                    setNewVenue({
                      ...newVenue,
                      google_place_id: e.target.value,
                    })
                  }
                />
              </label>
              <button className="primary" disabled={busy}>
                <Plus />
                Create pending venue
              </button>
            </form>
            <form className="panel stack-form" onSubmit={addFact}>
              <h3>Add sourced information</h3>
              <p className="muted small-text">
                Ordinary authoritative updates can publish automatically.
                Unusual changes still require review.
              </p>
              <label>
                Venue
                <select
                  required
                  value={fact.venue_id}
                  onChange={(e) =>
                    setFact({ ...fact, venue_id: e.target.value })
                  }
                >
                  <option value="">Choose a venue</option>
                  {data.venues.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Fact
                <select
                  value={fact.field}
                  onChange={(e) =>
                    setFact({ ...fact, field: e.target.value, value: "" })
                  }
                >
                  {[
                    "price_per_person",
                    "hours",
                    "closed",
                    "speciality",
                    "wheelchair",
                    "vegetarian",
                    "address",
                  ].map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </label>
              <label>
                Value
                <textarea
                  required
                  value={fact.value}
                  onChange={(e) => setFact({ ...fact, value: e.target.value })}
                  placeholder={
                    fact.field === "hours"
                      ? 'Weekly windows: {"0":[[600,1320]],"1":[[600,1320]]}. Monday=0. Minutes after midnight.'
                      : fact.field === "price_per_person"
                        ? "350"
                        : "Text, or true / false for a yes/no fact"
                  }
                />
              </label>
              <label>
                Source URL
                <input
                  required
                  type="url"
                  value={fact.source_url}
                  onChange={(e) =>
                    setFact({ ...fact, source_url: e.target.value })
                  }
                />
              </label>
              <label>
                Independent source identity
                <input
                  required
                  value={fact.source_group}
                  onChange={(e) =>
                    setFact({ ...fact, source_group: e.target.value })
                  }
                  placeholder="merchant-domain / source organisation"
                />
              </label>
              <label>
                Source authority
                <select
                  value={fact.source_type}
                  onChange={(e) =>
                    setFact({ ...fact, source_type: e.target.value })
                  }
                >
                  <option value="merchant">Merchant confirmed</option>
                  <option value="official">Official</option>
                  <option value="visitor">Visitor</option>
                  <option value="social">Social content</option>
                </select>
              </label>
              <button className="primary" disabled={busy}>
                Submit evidence
              </button>
              <p className="small-text muted">
                This form records an observation now with a one-day review
                expiry. Do not mark a source authoritative without checking it.
              </p>
            </form>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Place</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Publication</th>
                </tr>
              </thead>
              <tbody>
                {data.venues.map((v) => (
                  <tr key={v.id}>
                    <td>
                      <strong>{v.name}</strong>
                      <small>{v.area}</small>
                      <button
                        className="text-button"
                        onClick={() => setEditing(v)}
                      >
                        Edit planning details
                      </button>
                    </td>
                    <td>{v.category}</td>
                    <td>
                      <span className="status">{v.status}</span>
                    </td>
                    <td>
                      <button
                        className="text-button"
                        disabled={busy}
                        onClick={() =>
                          action(`/admin/venues/${v.id}/publish`, {
                            decision:
                              v.status === "published" ? "reject" : "approve",
                            reason:
                              v.status === "published"
                                ? "Administrator paused recommendations for review"
                                : "Administrator checked branch identity and essential evidence",
                          })
                        }
                      >
                        {v.status === "published"
                          ? "Pause for review"
                          : "Publish checked venue"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {tab === "jobs" && (
        <>
          <div className="panel job-controls">
            <div>
              <h3>Continuous care for the database</h3>
              <p className="small-text">
                {data.worker_heartbeat_age_seconds === null
                  ? "No background worker heartbeat recorded. Start the worker to process jobs continuously."
                  : `Last background worker heartbeat: ${data.worker_heartbeat_age_seconds} seconds ago. A long analysis can delay the next heartbeat.`}
              </p>
              <p className="muted">
                The separate worker claims durable jobs, retries failures and
                schedules refreshes. Running a job here processes one item.
              </p>
            </div>
            <div className="inline-actions">
              <button
                className="secondary"
                disabled={busy}
                onClick={() => action("/admin/refresh")}
              >
                <ArrowsClockwise />
                Queue due refreshes
              </button>
              <button
                className="primary"
                disabled={busy}
                onClick={() => action("/admin/jobs/run")}
              >
                <Play />
                {busy ? "Processing…" : "Process next job"}
              </button>
            </div>
            <form
              className="discovery-form"
              onSubmit={(e) => {
                e.preventDefault();
                action("/admin/discover", { query });
              }}
            >
              <label>
                Discovery query
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </label>
              <button className="secondary" disabled={busy}>
                Queue discovery
              </button>
            </form>
          </div>
          <div className="job-list">
            {data.jobs.map((j) => (
              <article className="panel" key={j.id}>
                <div className="submission-head">
                  <button
                    className="text-button"
                    onClick={() =>
                      setExpandedJob(expandedJob === j.id ? "" : j.id)
                    }
                  >
                    <strong>{j.kind}</strong>
                    <span className={`status ${j.state}`}>{j.state}</span>
                  </button>
                  <small>{j.attempts} attempts</small>
                </div>
                <p className="small-text muted">
                  Queued {dateText(j.created_at)}
                  {j.completed_at
                    ? ` · Completed ${dateText(j.completed_at)}`
                    : ` · Due ${dateText(j.due_at)}`}
                </p>
                {j.error && <p className="error">{j.error}</p>}
                {expandedJob === j.id && (
                  <pre className="json-view">
                    {JSON.stringify(j.result, null, 2)}
                  </pre>
                )}
                {j.state === "failed" && (
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => action(`/admin/jobs/${j.id}/retry`)}
                  >
                    Retry after resolving cause
                  </button>
                )}
              </article>
            ))}
          </div>
        </>
      )}
      {tab === "integrations" && (
        <>
          <div className="panel">
            <h3>Provider usage today</h3>
            <p>
              <strong>{data.provider_calls_today}</strong> /{" "}
              {data.provider_limit} allowed calls
            </p>
            <p className="small-text muted">
              This bounds call count, not currency. Configure provider-side
              billing limits as well. Keys are read only from the server
              environment.
            </p>
          </div>
          <div className="integration-grid">
            {data.integrations.map((i) => (
              <article className="panel" key={i.name}>
                <span
                  className={`status ${i.configured ? "accepted" : "review"}`}
                >
                  {i.configured
                    ? "Configured - check runtime status"
                    : "Not configured"}
                </span>
                <h3>{i.name}</h3>
                <p>{i.purpose}</p>
              </article>
            ))}
          </div>
        </>
      )}
      {tab === "audit" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {data.audit.map((a) => (
                <tr key={a.id}>
                  <td>{dateText(a.created_at)}</td>
                  <td>{a.action}</td>
                  <td>{JSON.stringify(a.detail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!data.audit.length && (
            <Empty title="No decisions recorded yet">
              Review and publication decisions are recorded here.
            </Empty>
          )}
        </div>
      )}
      {editing && (
        <OperationsEditor
          venue={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            load();
            onChanged();
          }}
        />
      )}
    </>
  );
}
