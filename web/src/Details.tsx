import { useState, type FormEvent } from "react";
import {
  ArrowUpRight,
  BookmarkSimple,
  CheckCircle,
  NavigationArrow,
  Lock,
  ArrowsClockwise,
} from "@phosphor-icons/react";
import { post, money, time, dateText, safeLink } from "./api";
import { Art, ErrorBox, Modal } from "./components";
import type { Venue, Plan, PlanResponse } from "./types";

export function PlanDetail({
  plan,
  onClose,
  onSave,
  onVenue,
  onRevised,
}: {
  plan: Plan;
  onClose: () => void;
  onSave: () => void;
  onVenue: (id: string) => void;
  onRevised: (r: PlanResponse) => void;
}) {
  const [locked, setLocked] = useState<string[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const r = plan.result;
  async function revise(exclude?: string) {
    setBusy(true);
    setError("");
    try {
      const response = await post<PlanResponse>("/plans", {
        ...plan.request,
        exclude_ids: exclude
          ? [...plan.request.exclude_ids, exclude]
          : plan.request.exclude_ids,
        lock_ids: locked.filter((x) => x !== exclude),
      });
      onRevised(response);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Your outing, at a glance" wide onClose={onClose}>
      <div className="plan-detail-intro">
        <div className="eyebrow">
          {r.is_demo ? "FICTIONAL DEMONSTRATION PLAN" : "YOUR PERSONAL PLAN"}
        </div>
        <h2>{r.title}</h2>
        <p>
          {dateText(plan.request.departure)} · {plan.request.party_size} people
          · From {plan.request.start_label}
        </p>
        <div className="detail-stats">
          <span>
            <strong>{r.total_minutes} min</strong>including a {r.time_buffer}
            -min buffer
          </span>
          <span>
            <strong>{money(r.total_cost)}</strong>estimated total for everyone
          </span>
          <span>
            <strong>{money(r.budget_remaining)}</strong>below your budget
          </span>
        </div>
        {plan.needs_refresh && (
          <div className="notice">
            This saved plan needs a fresh check. Venue facts may have changed.
          </div>
        )}
      </div>
      <div className="plan-detail-grid">
        <div>
          <div className="timeline-origin">
            <span className="timeline-number">
              <NavigationArrow />
            </span>
            <div>
              <strong>{time(plan.request.departure)} · Start</strong>
              <p>{plan.request.start_label}</p>
            </div>
          </div>
          {r.stops.map((s, i) => (
            <div className="timeline-stop" key={s.venue_id}>
              <div className="travel-line">
                {s.travel.minutes} min travel · {s.travel.km} km ·{" "}
                {money(s.travel.cost)} estimated
              </div>
              <div className="stop-head">
                <span className="timeline-number">{i + 1}</span>
                <div>
                  <span className="eyebrow">
                    {time(s.arrival)} arrival · {time(s.end)} finish
                  </span>
                  <button
                    className="text-button title-link"
                    onClick={() => onVenue(s.venue_id)}
                  >
                    <h3>{s.name}</h3>
                    <ArrowUpRight />
                  </button>
                  <p>{s.speciality}</p>
                  {s.offering && s.offering !== "Standard visit" && (
                    <p className="small-text">Selected: {s.offering}</p>
                  )}
                  <div className="stop-pills">
                    <span>{s.wait_minutes} min wait/check-in</span>
                    <span>{s.visit_minutes} min visit</span>
                  </div>
                  <p className="small-text">
                    {money(s.cost)} for {plan.request.party_size} +{" "}
                    {money(s.fees)} group fees
                  </p>
                  <div className="inline-actions">
                    <button
                      className={`text-button ${locked.includes(s.venue_id) ? "green" : ""}`}
                      onClick={() =>
                        setLocked(
                          locked.includes(s.venue_id)
                            ? locked.filter((x) => x !== s.venue_id)
                            : [...locked, s.venue_id],
                        )
                      }
                    >
                      <Lock size={16} />
                      {locked.includes(s.venue_id)
                        ? "Kept in revisions"
                        : "Keep this stop"}
                    </button>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => revise(s.venue_id)}
                    >
                      <ArrowsClockwise size={16} />
                      Swap this stop
                    </button>
                    {!r.is_demo && (
                      <a
                        target="_blank"
                        rel="noreferrer"
                        href={`https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}`}
                      >
                        <NavigationArrow size={16} />
                        Directions
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          <p className="timeline-end">
            Your outing ends here, with {r.time_buffer} minutes reserved for
            delays.
          </p>
        </div>
        <aside className="plan-summary">
          <h3>Why this works</h3>
          {r.reasons.map((x) => (
            <p className="reason" key={x}>
              <CheckCircle size={19} />
              {x}
            </p>
          ))}
          <hr />
          <h3>The budget</h3>
          {r.stops.map((s) => (
            <div className="cost-row" key={s.venue_id}>
              <span>{s.name}</span>
              <strong>{money(s.cost + s.fees)}</strong>
            </div>
          ))}
          <div className="cost-row">
            <span>Transport estimate</span>
            <strong>
              {money(r.stops.reduce((n, s) => n + s.travel.cost, 0))}
            </strong>
          </div>
          <div className="cost-row">
            <span>10% contingency</span>
            <strong>{money(r.reserve)}</strong>
          </div>
          <div className="cost-row total">
            <span>Total estimate</span>
            <strong>{money(r.total_cost)}</strong>
          </div>
          <button className="primary full" onClick={onSave}>
            <BookmarkSimple weight={plan.saved ? "fill" : "regular"} />
            {plan.saved ? "Remove from saved" : "Save this plan"}
          </button>
          <button
            className="secondary full"
            disabled={busy}
            onClick={() => revise()}
          >
            <ArrowsClockwise />
            {busy ? "Checking…" : "Recheck this plan"}
          </button>
        </aside>
      </div>
      <ErrorBox message={error} />
      <div className="small-text muted">
        {r.warnings.map((w) => (
          <p key={w}>{w}</p>
        ))}
        {r.is_demo && (
          <p>
            These venues and all associated prices, hours and routes are
            fictional. Do not travel using this demo.
          </p>
        )}
      </div>
    </Modal>
  );
}

export function VenueDetail({
  venue,
  onClose,
  onSave,
  onFeedback,
}: {
  venue: Venue;
  onClose: () => void;
  onSave: () => void;
  onFeedback: () => void;
}) {
  const [tab, setTab] = useState<
      "about" | "evidence" | "feedback" | "correction"
    >("about"),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const [rating, setRating] = useState(4),
    [dimension, setDimension] = useState(4),
    [value, setValue] = useState(4),
    [note, setNote] = useState(""),
    [occasion, setOccasion] = useState("casual"),
    [visitDate, setVisitDate] = useState(
      new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
    );
  const [field, setField] = useState("price_per_person"),
    [correction, setCorrection] = useState(""),
    [source, setSource] = useState("");
  const v = venue;
  async function feedback(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post("/visits", {
        venue_id: v.id,
        rating,
        dimensions: {
          [v.category === "food" || v.category === "cafe"
            ? "food"
            : "activity"]: dimension,
          value,
        },
        note,
        occasion,
        visited_on: visitDate,
      });
      setMessage("Visit recorded. Your feedback will help future suggestions.");
      onFeedback();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function report(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      let parsed: unknown = correction;
      if (field === "price_per_person") parsed = Number(correction);
      if (["closed", "wheelchair", "vegetarian"].includes(field))
        parsed = correction === "true";
      await post("/corrections", {
        venue_id: v.id,
        field,
        value: { value: parsed },
        source_url: source,
        source_type: "visitor",
        source_group: source,
        observed_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 86400000).toISOString(),
      });
      setMessage(
        "Report received. It will be checked before it changes recommendations.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={v.name} onClose={onClose}>
      <Art category={v.category} />
      <div className="venue-detail-heading">
        <div>
          <span className="eyebrow">
            {v.category} · {v.area}
          </span>
          <h2>{v.details.speciality || v.name}</h2>
        </div>
        <button
          className="icon-button"
          aria-label={v.saved ? "Unsave place" : "Save place"}
          onClick={onSave}
        >
          <BookmarkSimple size={24} weight={v.saved ? "fill" : "regular"} />
        </button>
      </div>
      {v.is_demo && (
        <div className="notice">
          Fictional demo venue. These details are for testing the app.
        </div>
      )}
      <div className="tabs" role="tablist">
        {(["about", "evidence", "feedback", "correction"] as const).map((t) => (
          <button
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? "active" : ""}
            key={t}
            onClick={() => {
              setTab(t);
              setError("");
              setMessage("");
            }}
          >
            {t === "about"
              ? "The place"
              : t === "evidence"
                ? "Sources"
                : t === "feedback"
                  ? "I visited"
                  : "Report a change"}
          </button>
        ))}
      </div>
      {tab === "about" && (
        <div className="detail-about">
          <p>{v.details.description || "A place under review."}</p>
          <div className="tag-row">
            {v.tags.map((t) => (
              <span className="tag" key={t}>
                {t}
              </span>
            ))}
          </div>
          <dl>
            <div>
              <dt>Typical spend</dt>
              <dd>
                {typeof v.details.price_per_person === "number"
                  ? money(v.details.price_per_person) + " per person"
                  : "Unconfirmed"}
              </dd>
            </div>
            <div>
              <dt>Time here</dt>
              <dd>
                {v.details.visit_minutes || "Unconfirmed"} minutes + estimated
                waiting
              </dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{v.address}</dd>
            </div>
            <div>
              <dt>Vegetarian options</dt>
              <dd>
                {v.details.vegetarian === true
                  ? "Recorded as available"
                  : v.details.vegetarian === false
                    ? "Not recorded as available"
                    : "Unknown"}
              </dd>
            </div>
            <div>
              <dt>Step-free access</dt>
              <dd>
                {v.details.wheelchair === true
                  ? "Recorded as available"
                  : "Unconfirmed / unavailable"}
              </dd>
            </div>
          </dl>
          {!v.is_demo && (
            <div className="inline-actions">
              <a
                className="secondary"
                target="_blank"
                rel="noreferrer"
                href={`https://www.google.com/maps/search/?api=1&query=${v.lat},${v.lng}`}
              >
                <NavigationArrow />
                Open in Maps
              </a>
              {safeLink(v.details.booking_url) && (
                <a
                  className="primary"
                  href={safeLink(v.details.booking_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Check booking options
                  <ArrowUpRight />
                </a>
              )}
            </div>
          )}
          <p className="small-text muted">
            A recorded option is not a guarantee of availability. Check
            allergies, access needs and current booking conditions directly with
            the venue.
          </p>
        </div>
      )}
      {tab === "evidence" && (
        <div>
          <p className="muted">
            Each fact keeps its own source and expiry. A fetch attempt does not
            count as successful verification.
          </p>
          {v.evidence.map((c) => (
            <article className="evidence-row" key={c.id}>
              <div>
                <strong>{c.field.replaceAll("_", " ")}</strong>
                <span className={`status ${c.status}`}>{c.status}</span>
              </div>
              <p className="evidence-value">{JSON.stringify(c.value.value)}</p>
              <p>{c.reason}</p>
              <small>
                Observed {dateText(c.observed_at)} · expires{" "}
                {dateText(c.expires_at)}
              </small>
              {safeLink(c.source_url) ? (
                <a
                  href={safeLink(c.source_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  View source
                  <ArrowUpRight />
                </a>
              ) : (
                <small className="muted">Demonstration source</small>
              )}
            </article>
          ))}
        </div>
      )}
      {tab === "feedback" && (
        <form onSubmit={feedback} className="stack-form">
          <p>
            Record a visit you actually made. Saving a place never counts as a
            visit.
          </p>
          <div className="two-col">
            <label>
              Visit date
              <input
                type="date"
                required
                max={new Date().toLocaleDateString("en-CA", {
                  timeZone: "Asia/Kolkata",
                })}
                value={visitDate}
                onChange={(e) => setVisitDate(e.target.value)}
              />
            </label>
            <label>
              Occasion
              <select
                value={occasion}
                onChange={(e) => setOccasion(e.target.value)}
              >
                <option value="casual">Casual outing</option>
                <option value="friends">With friends</option>
                <option value="family">Family time</option>
                <option value="date">A date</option>
                <option value="solo">Solo</option>
              </select>
            </label>
          </div>
          {[
            { label: "Overall experience", v: rating, set: setRating },
            {
              label:
                v.category === "food" || v.category === "cafe"
                  ? "Food / drink"
                  : "Activity",
              v: dimension,
              set: setDimension,
            },
            { label: "Value for money", v: value, set: setValue },
          ].map((s) => (
            <label key={s.label}>
              {s.label}
              <select value={s.v} onChange={(e) => s.set(+e.target.value)}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n} / 5 {n === 1 ? "· Poor" : n === 5 ? "· Loved it" : ""}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <label>
            What made it work, or not?
            <textarea
              value={note}
              maxLength={1000}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Loved the food; a little noisy for a quiet evening."
            />
          </label>
          <button className="primary" disabled={busy || !!message}>
            {busy ? "Saving…" : "Record my visit"}
          </button>
        </form>
      )}
      {tab === "correction" && (
        <form className="stack-form" onSubmit={report}>
          <p>Spotted a change? Share a specific fact and where you saw it.</p>
          <label>
            What changed?
            <select
              value={field}
              onChange={(e) => {
                setField(e.target.value);
                setCorrection("");
              }}
            >
              <option value="price_per_person">Price per person</option>
              <option value="closed">Closed status</option>
              <option value="address">Address</option>
              <option value="speciality">Speciality</option>
              <option value="wheelchair">Step-free access</option>
              <option value="vegetarian">Vegetarian options</option>
            </select>
          </label>
          <label>
            New information
            {["closed", "wheelchair", "vegetarian"].includes(field) ? (
              <select
                required
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
              >
                <option value="">Choose</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            ) : (
              <input
                required
                type={field === "price_per_person" ? "number" : "text"}
                min="0"
                maxLength={500}
                value={correction}
                onChange={(e) => setCorrection(e.target.value)}
              />
            )}
          </label>
          <label>
            Source link
            <input
              type="url"
              required
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <button className="primary" disabled={busy || !!message}>
            Submit for checking
          </button>
        </form>
      )}
      <ErrorBox message={error} />
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
    </Modal>
  );
}
