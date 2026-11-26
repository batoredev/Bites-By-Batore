import { useCallback, useEffect, useState } from "react";
import { api, post, safeLink } from "./api";
import { ErrorBox, Loading } from "./components";

// Operations > Approve places. The owner approves every place personally before customers
// can see it (decided 26 November 2026). One place at a time; no bulk approve.

type State = "waiting" | "changed" | "blocked" | "approved" | "rejected";
type Filter = State | "all";

interface Place {
  id: string;
  name: string;
  category: string;
  area: string;
  address: string;
  lat: number | null;
  lng: number | null;
  tags: string[];
  hours: Record<string, [number, number][]> | null;
  hours_basis: "checked" | "approx.";
  price_per_person: number | null;
  price_basis: "checked" | "approx.";
  fee_per_group: number | null;
  visit_minutes: number | null;
  max_group: number | null;
  min_age: number | null;
  child_friendly: boolean | null;
  vegetarian: boolean | null;
  sources: { type: string; url: string }[];
  source_groups: string[];
  last_seen: string | null;
  state: State;
  blockers: string[];
  hints: string[];
  decided_at: string | null;
  note: string;
  maps_link: string;
  embed: string;
}

interface Page {
  counts: Record<State, number>;
  total_places: number;
  categories: Record<string, number>;
  matching: number;
  items: Place[];
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: "waiting", label: "Waiting" },
  { key: "changed", label: "Changed since you approved" },
  { key: "blocked", label: "Can't publish yet" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
  { key: "all", label: "All" },
];
const STATE_WORDS: Record<State, string> = {
  waiting: "Waiting for you",
  changed: "A fact changed after you approved it",
  blocked: "Can't be approved yet",
  approved: "Approved: customers will see it",
  rejected: "Rejected: customers won't see it",
};
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const clock = (m: number) => {
  const h = Math.floor(m / 60) % 24;
  return `${h % 12 || 12}${m % 60 ? ":" + String(m % 60).padStart(2, "0") : ""}${h < 12 ? "am" : "pm"}`;
};

export function hoursText(hours: Place["hours"]): string {
  if (!hours || !Object.keys(hours).length) return "Not known";
  const day = (d: number) =>
    (hours[String(d)] || []).map(([a, b]) => `${clock(a)}–${clock(b)}`).join(", ") || "closed";
  const all = DAYS.map((_, d) => day(d));
  if (all.every((t) => t === all[0])) return `Every day ${all[0]}`;
  return DAYS.map((name, d) => `${name} ${all[d]}`).join(" · ");
}

const host = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};

export default function PublishApproval() {
  const [filter, setFilter] = useState<Filter>("waiting");
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState<Page | null>(null);
  const [index, setIndex] = useState(0);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [last, setLast] = useState<{ place: Place; previous: State } | null>(null);

  const path = useCallback(() => {
    const params = new URLSearchParams({ state: filter, limit: "100" });
    if (category) params.set("category", category);
    if (query.trim()) params.set("q", query.trim());
    return `/admin/publish/places?${params}`;
  }, [filter, category, query]);

  useEffect(() => {
    let live = true;
    setError("");
    api<Page>(path())
      .then((p) => {
        if (!live) return;
        setPage(p);
        setIndex(0);
      })
      .catch((e) => live && setError((e as Error).message));
    return () => {
      live = false;
    };
  }, [path]);

  const item = page?.items[index];
  useEffect(() => setNote(item?.note || ""), [item?.id, item?.note]);

  const decide = useCallback(
    async (decision: "approve" | "reject" | "clear", target?: Place) => {
      const place = target || item;
      if (!page || !place || busy) return;
      setBusy(true);
      setError("");
      try {
        await post<Place>("/admin/publish/decide", {
          venue_id: place.id,
          decision,
          note: decision === "clear" ? "" : note,
        });
        if (!target) setLast({ place, previous: place.state });
        const fresh = await api<Page>(path());
        setPage(fresh);
        // The place just decided may leave this view; stay at the same position so the next one shows.
        const stays = fresh.items.findIndex((p) => p.id === place.id);
        const next = stays >= 0 ? stays + 1 : index;
        setIndex(Math.max(0, Math.min(next, fresh.items.length - 1)));
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [page, item, busy, note, path, index],
  );

  const undo = useCallback(async () => {
    if (!last) return;
    const back = last.previous === "approved" ? "approve" : last.previous === "rejected" ? "reject" : "clear";
    setLast(null);
    await decide(back, last.place);
  }, [last, decide]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = (e.target as HTMLElement)?.closest("input, textarea, select");
      if (typing || e.ctrlKey || e.metaKey || e.altKey || !page) return;
      const k = e.key.toLowerCase();
      if (k === "a" && item && !item.blockers.length) void decide("approve");
      else if (k === "r" && item) void decide("reject");
      else if (k === "s" || e.key === "ArrowRight") setIndex((i) => Math.min(i + 1, Math.max(page.items.length - 1, 0)));
      else if (e.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
      else if (k === "u") void undo();
      else if (k === "m" && item) {
        const link = safeLink(item.maps_link);
        if (link) window.open(link, "_blank", "noreferrer");
      } else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [page, item, decide, undo]);

  if (!page) return error ? <ErrorBox message={error} /> : <Loading label="Loading places" />;

  const decided = page.counts.approved + page.counts.rejected;
  const pct = page.total_places ? Math.round((decided / page.total_places) * 100) : 0;
  const mapLink = item && safeLink(item.maps_link);
  const facts = item
    ? [
        item.visit_minutes ? `about ${item.visit_minutes} min` : null,
        item.max_group ? `up to ${item.max_group} people` : null,
        item.min_age ? `age ${item.min_age}+` : null,
        item.child_friendly ? "child friendly" : null,
        item.vegetarian ? "vegetarian" : null,
      ].filter(Boolean)
    : [];

  return (
    <section className="desk" aria-label="Approve places">
      <header className="desk-bar">
        <div className="desk-progress" aria-label={`${decided} of ${page.total_places} decided`}>
          <span className="desk-count">
            {decided}
            <small>/{page.total_places}</small>
          </span>
          <span className="desk-meter">
            <span style={{ transform: `scaleX(${pct / 100})` }} />
          </span>
        </div>
        <span className="desk-sheet">{page.counts.approved} approved · customers see only places you approve</span>
      </header>

      <div className="approve-filters" role="group" aria-label="Which places">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={filter === f.key ? "active" : ""}
            aria-pressed={filter === f.key}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
            {f.key !== "all" && <span>{page.counts[f.key as State]}</span>}
          </button>
        ))}
        <select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Every category</option>
          {Object.entries(page.categories).map(([c, n]) => (
            <option key={c} value={c}>
              {c.replace("_", " ")} ({n})
            </option>
          ))}
        </select>
        <input
          type="search"
          aria-label="Find a place"
          placeholder="Find by name or area"
          value={query}
          maxLength={100}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <ErrorBox message={error} />

      {!item ? (
        <p className="desk-empty">
          {filter === "waiting" && !category && !query
            ? "Nothing is waiting. Every live place has your decision."
            : "No places match this view."}
        </p>
      ) : (
        <div className="desk-grid">
          <article className="desk-card" aria-live="polite" key={item.id}>
            <p className="desk-kicker">
              {STATE_WORDS[item.state]} · {index + 1} of {page.matching}
            </p>
            <h3>{item.name}</h3>
            <p className="desk-claim">
              A {item.category.replace("_", " ")} in {item.area || "Coimbatore"}
              {item.address ? ` · ${item.address}` : ""}
            </p>

            {item.blockers.length > 0 && (
              <ul className="approve-blockers" aria-label="Why it can't be approved yet">
                {item.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            )}
            <ul className="desk-hints">
              {item.hints.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>

            <div className="desk-evidence">
              <dl>
                <dt>Price</dt>
                <dd>
                  {item.price_per_person != null ? `₹${item.price_per_person} per person` : "Not known"}{" "}
                  <span className={"approve-basis" + (item.price_basis === "checked" ? " ok" : "")}>{item.price_basis}</span>
                </dd>
                <dt>Open</dt>
                <dd>
                  {hoursText(item.hours)}{" "}
                  <span className={"approve-basis" + (item.hours_basis === "checked" ? " ok" : "")}>{item.hours_basis}</span>
                </dd>
                {item.fee_per_group ? (
                  <>
                    <dt>Group fee</dt>
                    <dd>₹{item.fee_per_group}</dd>
                  </>
                ) : null}
                <dt>Visit</dt>
                <dd>{facts.join(" · ") || "No details"}</dd>
                {item.tags.length > 0 && (
                  <>
                    <dt>Tags</dt>
                    <dd>{item.tags.join(", ")}</dd>
                  </>
                )}
                <dt>Sources</dt>
                <dd className="approve-sources">
                  {item.sources.length
                    ? item.sources.map((s) => {
                        const link = safeLink(s.url);
                        return link ? (
                          <a key={s.url} href={link} target="_blank" rel="noreferrer">
                            {s.type.replace("_", " ")} · {host(s.url)}
                          </a>
                        ) : null;
                      })
                    : "none with a public link"}
                </dd>
                {item.decided_at && (
                  <>
                    <dt>Decided</dt>
                    <dd>{new Date(item.decided_at).toLocaleString("en-IN")}</dd>
                  </>
                )}
              </dl>
            </div>

            <label className="approve-note">
              Note, kept with your decision (optional)
              <input
                value={note}
                maxLength={500}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. went there in October"
              />
            </label>

            <div className="desk-actions">
              <button
                className={"desk-answer desk-yes" + (item.state === "approved" ? " chosen" : "")}
                disabled={busy || item.blockers.length > 0}
                title={item.blockers.length ? "Fix the problems above first" : "Customers will see this place"}
                onClick={() => decide("approve")}
              >
                Approve<kbd>A</kbd>
              </button>
              <button
                className={"desk-answer desk-no" + (item.state === "rejected" ? " chosen" : "")}
                disabled={busy}
                onClick={() => decide("reject")}
              >
                Reject<kbd>R</kbd>
              </button>
            </div>
            <div className="desk-nav">
              <button onClick={() => setIndex((i) => Math.max(i - 1, 0))}>← Back</button>
              <button onClick={() => setIndex((i) => Math.min(i + 1, page.items.length - 1))}>
                Skip <kbd>S</kbd>
              </button>
              <button onClick={undo} disabled={!last || busy}>
                Undo <kbd>U</kbd>
              </button>
              {item.state !== "waiting" && item.state !== "blocked" && (
                <button onClick={() => decide("clear")} disabled={busy}>
                  Back to waiting
                </button>
              )}
              {mapLink && (
                <a href={mapLink} target="_blank" rel="noreferrer">
                  Open in Maps <kbd>M</kbd>
                </a>
              )}
            </div>
          </article>

          <div className="desk-side">
            <iframe
              key={item.embed}
              className="desk-map"
              title={`Map of ${item.name}`}
              src={item.embed}
              referrerPolicy="no-referrer"
            />
          </div>
        </div>
      )}
      {page.matching > page.items.length && (
        <p className="desk-tip">
          Showing the first {page.items.length} of {page.matching}. Decide these and the next ones load.
        </p>
      )}
    </section>
  );
}
