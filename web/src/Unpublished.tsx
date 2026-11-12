import { useEffect, useMemo, useState } from "react";
import { api, dateText, safeLink } from "./api";
import { ErrorBox, categories } from "./components";

type Place = {
  id: string;
  name: string;
  category: string;
  area: string;
  status: string;
  reason_kind: string;
  reason: string;
  has_coordinates: boolean;
  has_price: boolean;
  has_hours: boolean;
  source: "instagram" | "directory" | "web";
  source_count: number;
  source_url: string;
  offerings: string[];
  updated_at: string;
  map_search_url: string;
};

const REASONS: Record<string, string> = {
  no_coordinates: "No map coordinates",
  held: "Held: name needs review",
  duplicate: "Held: possible duplicate",
  ready: "Ready, not yet published",
  awaiting_approval: "Awaiting approval",
  merged: "Merged into another",
  rejected: "Rejected",
};
const SOURCES: Record<string, string> = {
  instagram: "Instagram reel",
  directory: "OpenStreetMap directory",
  web: "Web page",
};
const PAGE = 100;

export default function Unpublished() {
  const [places, setPlaces] = useState<Place[] | null>(null),
    [published, setPublished] = useState(0),
    [error, setError] = useState("");
  const [search, setSearch] = useState(""),
    [category, setCategory] = useState(""),
    [reason, setReason] = useState(""),
    [source, setSource] = useState(""),
    [area, setArea] = useState(""),
    [coordinates, setCoordinates] = useState(""),
    [sort, setSort] = useState("updated"),
    [shown, setShown] = useState(PAGE);

  useEffect(() => {
    api<{ places: Place[]; published: number }>("/admin/spots/unpublished")
      .then((r) => {
        setPlaces(r.places);
        setPublished(r.published);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  const areas = useMemo(
    () =>
      [...new Set((places || []).map((p) => p.area).filter(Boolean))].sort(),
    [places],
  );
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const p of places || [])
      result[p.reason_kind] = (result[p.reason_kind] || 0) + 1;
    return result;
  }, [places]);
  const filtered = useMemo(() => {
    const words = search.toLowerCase().trim();
    const rows = (places || []).filter(
      (p) =>
        (!words ||
          p.name.toLowerCase().includes(words) ||
          p.offerings.some((o) => o.toLowerCase().includes(words))) &&
        (!category || p.category === category) &&
        (!reason || p.reason_kind === reason) &&
        (!source || p.source === source) &&
        (!area || (area === "(none)" ? !p.area : p.area === area)) &&
        (!coordinates || (coordinates === "yes") === p.has_coordinates),
    );
    if (sort === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
    if (sort === "sources") rows.sort((a, b) => b.source_count - a.source_count);
    return rows;
  }, [places, search, category, reason, source, area, coordinates, sort]);

  useEffect(() => setShown(PAGE), [filtered]);
  const active = [search, category, reason, source, area, coordinates].some(
    Boolean,
  );
  function clear() {
    setSearch("");
    setCategory("");
    setReason("");
    setSource("");
    setArea("");
    setCoordinates("");
  }
  const label = (id: string) =>
    categories.find((c) => c.id === id)?.label || id;

  return (
    <section aria-labelledby="unpublished-title">
      <div className="section-heading">
        <div>
          <div className="eyebrow">NOT IN THE PLANNER</div>
          <h2 id="unpublished-title">Unpublished places</h2>
        </div>
        <span className="muted">
          {places
            ? `${places.length} unpublished · ${published} published`
            : "Loading…"}
        </span>
      </div>
      <p className="muted">
        Places the agent has collected that the itinerary planner cannot use
        yet, and why. Names and details here are unverified.
      </p>
      <ErrorBox message={error} />
      {places && (
        <>
          <div className="category-row" role="group" aria-label="Reason">
            <button
              className={`chip ${reason === "" ? "active" : ""}`}
              aria-pressed={reason === ""}
              onClick={() => setReason("")}
            >
              All ({places.length})
            </button>
            {Object.keys(REASONS)
              .filter((k) => counts[k])
              .map((k) => (
                <button
                  key={k}
                  className={`chip ${reason === k ? "active" : ""}`}
                  aria-pressed={reason === k}
                  onClick={() => setReason(reason === k ? "" : k)}
                >
                  {REASONS[k]} ({counts[k]})
                </button>
              ))}
          </div>
          <div className="parameter-grid unpublished-filters">
            <label>
              Search name or dish
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="biryani, cafe name…"
              />
            </label>
            <label>
              Category
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Area
              <select value={area} onChange={(e) => setArea(e.target.value)}>
                <option value="">All areas</option>
                <option value="(none)">No area recorded</option>
                {areas.map((a) => (
                  <option key={a}>{a}</option>
                ))}
              </select>
            </label>
            <label>
              Found through
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="">Any source</option>
                {Object.entries(SOURCES).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Map coordinates
              <select
                value={coordinates}
                onChange={(e) => setCoordinates(e.target.value)}
              >
                <option value="">Either</option>
                <option value="yes">Has coordinates</option>
                <option value="no">Missing coordinates</option>
              </select>
            </label>
            <label>
              Sort by
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="updated">Recently updated</option>
                <option value="name">Name</option>
                <option value="sources">Most sources</option>
              </select>
            </label>
          </div>
          <p className="muted" aria-live="polite">
            Showing {Math.min(shown, filtered.length)} of {filtered.length}
            {active ? " matching places. " : " places. "}
            {active && (
              <button className="text-button" onClick={clear}>
                Clear filters
              </button>
            )}
          </p>
          {filtered.length === 0 ? (
            <div className="notice">No places match these filters.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Place</th>
                    <th>Category</th>
                    <th>Area</th>
                    <th>Why it is not published</th>
                    <th>Has</th>
                    <th>Source</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, shown).map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong>{p.name}</strong>
                        {p.offerings.length > 0 && (
                          <small>{p.offerings.join(" · ")}</small>
                        )}
                        <a
                          className="text-button"
                          href={safeLink(p.map_search_url)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Search on Maps
                        </a>
                      </td>
                      <td>{label(p.category)}</td>
                      <td>{p.area || "—"}</td>
                      <td>
                        <span
                          className={`status ${p.reason_kind === "ready" ? "accepted" : p.reason_kind === "no_coordinates" ? "pending" : "rejected"}`}
                        >
                          {REASONS[p.reason_kind] || p.status}
                        </span>
                        {p.reason_kind === "held" ||
                        p.reason_kind === "duplicate" ? (
                          <small>{p.reason}</small>
                        ) : null}
                      </td>
                      <td>
                        <small>
                          {[
                            p.has_coordinates && "coordinates",
                            p.has_price && "price",
                            p.has_hours && "hours",
                          ]
                            .filter(Boolean)
                            .join(", ") || "none of coordinates, price, hours"}
                        </small>
                      </td>
                      <td>
                        {p.source_url ? (
                          <a
                            href={safeLink(p.source_url)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {SOURCES[p.source]}
                          </a>
                        ) : (
                          SOURCES[p.source]
                        )}
                        <small>
                          {p.source_count} source
                          {p.source_count === 1 ? "" : "s"}
                        </small>
                      </td>
                      <td>{dateText(p.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {shown < filtered.length && (
            <button
              className="secondary"
              onClick={() => setShown(shown + PAGE)}
            >
              Show {Math.min(PAGE, filtered.length - shown)} more
            </button>
          )}
        </>
      )}
    </section>
  );
}
