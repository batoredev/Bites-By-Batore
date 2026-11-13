import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, dateText, post, safeLink } from "./api";
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
  edited_by_you: boolean;
  source: "instagram" | "directory" | "web" | "owner";
  source_count: number;
  source_url: string;
  offerings: string[];
  updated_at: string;
  map_search_url: string;
};
type Learned = {
  rejected_names: string[];
  category_by_name: number;
  category_by_word: Record<string, string>;
  blocked_creators: string[];
  renames: { from: string; to: string }[];
  places_added_by_you: number;
};

const REASONS: Record<string, string> = {
  no_coordinates: "No map coordinates",
  held: "Held: name needs review",
  duplicate: "Held: possible duplicate",
  ready: "Ready, not yet published",
  awaiting_approval: "Awaiting approval",
  rejected: "Rejected by you",
  merged: "Merged into another",
  published: "Published",
};
const SOURCES: Record<string, string> = {
  owner: "Added by you",
  instagram: "Instagram reel",
  directory: "OpenStreetMap directory",
  web: "Web page",
};
const REJECT_KINDS: [string, string][] = [
  ["not_a_venue", "Not a real place (never suggest this name again)"],
  ["out_of_scope", "Not food or entertainment (never suggest again)"],
  ["wrong_city", "Not in Coimbatore (never suggest again)"],
  ["closed", "Closed down"],
  ["other", "Other"],
];
const PAGE = 100;

export default function Unpublished({ onChanged }: { onChanged?: () => void }) {
  const [places, setPlaces] = useState<Place[] | null>(null),
    [published, setPublished] = useState(0),
    [learned, setLearned] = useState<Learned | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const [search, setSearch] = useState(""),
    [category, setCategory] = useState(""),
    [reason, setReason] = useState(""),
    [source, setSource] = useState(""),
    [area, setArea] = useState(""),
    [coordinates, setCoordinates] = useState(""),
    [sort, setSort] = useState("updated"),
    [includePublished, setIncludePublished] = useState(false),
    [shown, setShown] = useState(PAGE);
  const [editing, setEditing] = useState<Place | null>(null),
    [draft, setDraft] = useState({ name: "", category: "", area: "", maps_url: "" });
  const [rejecting, setRejecting] = useState<Place | null>(null),
    [rejection, setRejection] = useState({ kind: "not_a_venue", block_creator: false });
  const [adding, setAdding] = useState({
    names: "",
    category: "",
    area: "",
    maps_url: "",
    investigate: true,
  });

  async function load() {
    try {
      const [list, rules] = await Promise.all([
        api<{ places: Place[]; published: number }>(
          `/admin/spots/unpublished?include_published=${includePublished}`,
        ),
        api<Learned>("/admin/spots/learned"),
      ]);
      setPlaces(list.places);
      setPublished(list.published);
      setLearned(rules);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void load();
  }, [includePublished]);

  async function act(run: () => Promise<string>) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setMessage(await run());
      await load();
      onChanged?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

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

  useEffect(() => setShown(PAGE), [search, category, reason, source, area, coordinates, sort]);
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

  function startEdit(p: Place) {
    setRejecting(null);
    setEditing(p);
    setDraft({ name: p.name, category: p.category, area: p.area, maps_url: "" });
  }
  function saveEdit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const p = editing;
    void act(async () => {
      await post(`/admin/spots/${p.id}/edit`, {
        ...(draft.name.trim() !== p.name ? { name: draft.name.trim() } : {}),
        category: draft.category,
        ...(draft.area.trim() !== p.area ? { area: draft.area.trim() } : {}),
        ...(draft.maps_url.trim() ? { maps_url: draft.maps_url.trim() } : {}),
      });
      setEditing(null);
      return `Saved "${draft.name.trim()}". The agent will reuse this correction.`;
    });
  }
  function addPlaces(e: FormEvent) {
    e.preventDefault();
    const names = adding.names
      .split("\n")
      .map((n) => n.trim())
      .filter((n) => n.length >= 2);
    if (!names.length) return setError("Enter at least one place name.");
    void act(async () => {
      const r = await post<{
        added: string[];
        already_listed: string[];
        investigations_started: number;
      }>("/admin/spots/add", {
        names,
        area: adding.area.trim(),
        maps_url: adding.maps_url.trim(),
        investigate: adding.investigate,
        ...(adding.category ? { category: adding.category } : {}),
      });
      setAdding({ ...adding, names: "", maps_url: "" });
      return (
        `Added ${r.added.length} place${r.added.length === 1 ? "" : "s"}` +
        (r.already_listed.length
          ? `; already listed: ${r.already_listed.join(", ")}`
          : "") +
        (r.investigations_started
          ? `. The agent will research ${r.investigations_started} of them.`
          : ".")
      );
    });
  }

  return (
    <section aria-labelledby="unpublished-title">
      <div className="section-heading">
        <div>
          <div className="eyebrow">YOUR PLACES</div>
          <h2 id="unpublished-title">Place manager</h2>
        </div>
        <span className="muted">
          {places
            ? `${places.filter((p) => p.reason_kind !== "published").length} unpublished · ${published} published`
            : "Loading…"}
        </span>
      </div>
      <p className="muted">
        Every place the agent has collected that the planner cannot use yet,
        and why. Correct, release or reject them here; the agent keeps each
        correction and applies it to later finds. Details are unverified.
      </p>
      <ErrorBox message={error} />
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}

      <details className="exclusions">
        <summary>Add places you know</summary>
        <form onSubmit={addPlaces}>
          <div className="parameter-grid unpublished-filters">
            <label className="wide-field">
              Place names, one per line
              <textarea
                rows={4}
                value={adding.names}
                onChange={(e) => setAdding({ ...adding, names: e.target.value })}
                placeholder={"Example Cafe\nExample Bowling Arena"}
              />
            </label>
            <label>
              Category (optional)
              <select
                value={adding.category}
                onChange={(e) =>
                  setAdding({ ...adding, category: e.target.value })
                }
              >
                <option value="">Let the agent decide</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Area (optional)
              <input
                value={adding.area}
                onChange={(e) => setAdding({ ...adding, area: e.target.value })}
                placeholder="RS Puram"
              />
            </label>
            <label className="wide-field">
              Google Maps link (optional, one place only)
              <input
                type="url"
                value={adding.maps_url}
                onChange={(e) =>
                  setAdding({ ...adding, maps_url: e.target.value })
                }
                placeholder="https://www.google.com/maps/place/…/@11.0,76.9,17z"
              />
            </label>
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={adding.investigate}
              onChange={(e) =>
                setAdding({ ...adding, investigate: e.target.checked })
              }
            />
            Have the agent search for reels, menus and details for these places
          </label>
          <p className="muted">
            A place needs coordinates before the planner can use it. A Maps
            link whose address contains “@latitude,longitude” supplies them.
          </p>
          <button className="primary" disabled={busy}>
            Add places
          </button>
        </form>
      </details>

      {learned && (
        <details className="exclusions">
          <summary>
            What the agent has learned from you (
            {learned.rejected_names.length +
              learned.category_by_name +
              learned.blocked_creators.length +
              learned.renames.length}{" "}
            rules)
          </summary>
          <ul>
            <li>
              <strong>{learned.rejected_names.length}</strong> names it will
              never propose again
              {learned.rejected_names.length > 0 &&
                `: ${learned.rejected_names.slice(0, 20).join(", ")}`}
            </li>
            <li>
              <strong>{learned.category_by_name}</strong> names with a category
              you set
              {Object.keys(learned.category_by_word).length > 0 &&
                `; words it now maps to a category: ${Object.entries(
                  learned.category_by_word,
                )
                  .map(([w, c]) => `${w} → ${label(c)}`)
                  .join(", ")}`}
            </li>
            <li>
              <strong>{learned.renames.length}</strong> name corrections
              {learned.renames.length > 0 &&
                `: ${learned.renames
                  .slice(-8)
                  .map((r) => `${r.from} → ${r.to}`)
                  .join("; ")}`}
            </li>
            <li>
              <strong>{learned.blocked_creators.length}</strong> creators it
              skips
              {learned.blocked_creators.length > 0 &&
                `: ${learned.blocked_creators.join(", ")}`}
            </li>
            <li>
              <strong>{learned.places_added_by_you}</strong> places you added
              yourself
            </li>
          </ul>
          <p className="muted">
            These are rules from your edits, not model training. Restoring a
            rejected place removes its rule.
          </p>
        </details>
      )}

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
          <div className="form-bottom">
            <label className="check-row">
              <input
                type="checkbox"
                checked={includePublished}
                onChange={(e) => setIncludePublished(e.target.checked)}
              />
              Also show published places
            </label>
            {(counts.ready || 0) > 0 && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const r = await post<{ published: number }>(
                      "/admin/spots/publish-ready",
                    );
                    return `Published ${r.published} place${r.published === 1 ? "" : "s"} to the test inventory.`;
                  })
                }
              >
                Publish ready places
              </button>
            )}
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
                    <th>Status</th>
                    <th>Has</th>
                    <th>Source</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, shown).map((p) =>
                    editing?.id === p.id ? (
                      <tr key={p.id}>
                        <td colSpan={7}>
                          <form onSubmit={saveEdit}>
                            <div className="parameter-grid unpublished-filters">
                              <label>
                                Name
                                <input
                                  required
                                  minLength={2}
                                  maxLength={150}
                                  value={draft.name}
                                  onChange={(e) =>
                                    setDraft({ ...draft, name: e.target.value })
                                  }
                                />
                              </label>
                              <label>
                                Category
                                <select
                                  value={draft.category}
                                  onChange={(e) =>
                                    setDraft({
                                      ...draft,
                                      category: e.target.value,
                                    })
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
                                Area
                                <input
                                  maxLength={100}
                                  value={draft.area}
                                  onChange={(e) =>
                                    setDraft({ ...draft, area: e.target.value })
                                  }
                                />
                              </label>
                              <label>
                                Google Maps link (sets coordinates)
                                <input
                                  type="url"
                                  value={draft.maps_url}
                                  onChange={(e) =>
                                    setDraft({
                                      ...draft,
                                      maps_url: e.target.value,
                                    })
                                  }
                                  placeholder="…/@11.0,76.9,17z"
                                />
                              </label>
                            </div>
                            <div className="form-bottom">
                              <button className="primary" disabled={busy}>
                                Save correction
                              </button>
                              <button
                                type="button"
                                className="secondary"
                                onClick={() => setEditing(null)}
                              >
                                Cancel
                              </button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    ) : rejecting?.id === p.id ? (
                      <tr key={p.id}>
                        <td colSpan={7}>
                          <strong>Remove “{p.name}”</strong>
                          <div className="parameter-grid unpublished-filters">
                            <label>
                              Why
                              <select
                                value={rejection.kind}
                                onChange={(e) =>
                                  setRejection({
                                    ...rejection,
                                    kind: e.target.value,
                                  })
                                }
                              >
                                {REJECT_KINDS.map(([k, v]) => (
                                  <option key={k} value={k}>
                                    {v}
                                  </option>
                                ))}
                              </select>
                            </label>
                          </div>
                          {p.source === "instagram" && (
                            <label className="check-row">
                              <input
                                type="checkbox"
                                checked={rejection.block_creator}
                                onChange={(e) =>
                                  setRejection({
                                    ...rejection,
                                    block_creator: e.target.checked,
                                  })
                                }
                              />
                              Also skip future reels from the creator of this
                              reel
                            </label>
                          )}
                          <div className="form-bottom">
                            <button
                              className="danger-button"
                              disabled={busy}
                              onClick={() =>
                                void act(async () => {
                                  const r = await post<{ also_held: number }>(
                                    `/admin/spots/${p.id}/reject`,
                                    rejection,
                                  );
                                  setRejecting(null);
                                  return (
                                    `Removed "${p.name}".` +
                                    (r.also_held
                                      ? ` ${r.also_held} other record(s) with the same name were held.`
                                      : "")
                                  );
                                })
                              }
                            >
                              Remove place
                            </button>
                            <button
                              className="secondary"
                              onClick={() => setRejecting(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      <tr key={p.id}>
                        <td>
                          <strong>{p.name}</strong>
                          {p.edited_by_you && <small>Edited by you</small>}
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
                            className={`status ${p.reason_kind === "ready" || p.reason_kind === "published" ? "accepted" : p.reason_kind === "no_coordinates" ? "pending" : "rejected"}`}
                          >
                            {REASONS[p.reason_kind] || p.status}
                          </span>
                          {["held", "duplicate", "rejected"].includes(
                            p.reason_kind,
                          ) && <small>{p.reason}</small>}
                          <small>Updated {dateText(p.updated_at)}</small>
                        </td>
                        <td>
                          <small>
                            {[
                              p.has_coordinates && "coordinates",
                              p.has_price && "price",
                              p.has_hours && "hours",
                            ]
                              .filter(Boolean)
                              .join(", ") || "nothing yet"}
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
                        <td>
                          {p.status === "rejected" ? (
                            <button
                              className="text-button"
                              disabled={busy}
                              onClick={() =>
                                void act(async () => {
                                  await post(`/admin/spots/${p.id}/restore`);
                                  return `Restored "${p.name}".`;
                                })
                              }
                            >
                              Restore
                            </button>
                          ) : p.status === "merged" ? (
                            <small>No actions</small>
                          ) : (
                            <>
                              <button
                                className="text-button"
                                onClick={() => startEdit(p)}
                              >
                                Edit
                              </button>
                              {p.status === "quarantined" && (
                                <button
                                  className="text-button"
                                  disabled={busy}
                                  onClick={() =>
                                    void act(async () => {
                                      await post(`/admin/spots/${p.id}/edit`, {
                                        release: true,
                                      });
                                      return `Released "${p.name}": you confirmed it is a real place.`;
                                    })
                                  }
                                >
                                  It is real
                                </button>
                              )}
                              <button
                                className="text-button"
                                onClick={() => {
                                  setEditing(null);
                                  setRejecting(p);
                                  setRejection({
                                    kind: "not_a_venue",
                                    block_creator: false,
                                  });
                                }}
                              >
                                Remove
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    ),
                  )}
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
