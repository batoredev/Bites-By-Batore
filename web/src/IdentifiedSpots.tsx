import { useEffect, useState, type FormEvent } from "react";
import { api, post, dateText, money } from "./api";
import { ErrorBox, Loading, Modal, categories } from "./components";

interface Spot {
  id: string;
  name: string;
  category: string;
  area: string;
  status: string;
  venue_id: string;
  updated_at: string;
  missing: string[];
  map_search_url: string;
  data: {
    name_status?: string;
    maps_identity?: { maps_url: string; name: string; confirmed_by: string };
    aliases?: string[];
    possible_duplicates?: string[];
    quality_issues?: string[];
    merged_into?: string;
    address?: string;
    hours?: string;
    coordinates?: { lat: number; lng: number; basis: string };
    maps_links?: string[];
    menu_links?: string[];
    offerings?: {
      name: string;
      price_inr: number | null;
      unit: string;
      source_url: string;
      basis: string;
    }[];
    vibes?: {
      tag: string;
      evidence?: string;
      source_url: string;
      basis: string;
    }[];
    sources?: {
      url: string;
      type: string;
      collected_at: string;
      published_at?: string | null;
      basis: string;
    }[];
    review_notes?: string[];
  };
}

function Prepare({
  spot,
  close,
  saved,
}: {
  spot: Spot;
  close: () => void;
  saved: () => void;
}) {
  const [form, setForm] = useState({
    name: spot.name,
    category: spot.category,
    area: spot.area,
    address: spot.data.address || "",
    lat: spot.data.coordinates?.lat?.toString() || "",
    lng: spot.data.coordinates?.lng?.toString() || "",
    evidence_url: "",
    maps_url: spot.data.maps_identity?.maps_url || "",
    reason: "",
    checked: false,
    maps_checked: false,
  });
  const [mapsResult, setMapsResult] = useState<{
    status: string; reason?: string;
    candidates: { id: string; displayName?: { text: string }; formattedAddress?: string; googleMapsUri?: string }[];
  } | null>(null);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(`/admin/spots/${spot.id}/prepare`, {
        venue: {
          name: form.name,
          category: form.category,
          area: form.area,
          address: form.address,
          lat: Number(form.lat),
          lng: Number(form.lng),
          tags: [],
          details: { branch_confirmed: form.checked },
        },
        evidence_url: form.evidence_url,
        reason: form.reason,
        maps_url: form.maps_url,
        maps_name_checked: form.maps_checked,
      });
      saved();
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title={`Prepare ${spot.name} for approval`} onClose={close}>
      <form className="stack-form" onSubmit={submit}>
        <p>
          Confirm the branch here. Then review its current price, hours and
          operating status in Venue desk and approve the location. It stays out
          of suggestions until that approval.
        </p>
        <ErrorBox message={error} />
        <p>The location name must match the exact Google Maps branch. Keep nicknames as aliases. Use independent branch evidence for your saved address and coordinates.</p>
        <a href={spot.map_search_url} target="_blank" rel="noreferrer">Open Google Maps to check this branch</a>
        <button type="button" className="secondary" disabled={busy} onClick={async () => {
          setBusy(true);
          try { setMapsResult(await post(`/admin/spots/${spot.id}/maps-candidates`)); }
          catch (e) { setError((e as Error).message); }
          finally { setBusy(false); }
        }}>Look up Maps candidates</button>
        {mapsResult && <div role="status">
          {mapsResult.status === "unavailable" ? <p>{mapsResult.reason}. Open Maps above to check the name manually.</p> : <>
            <p>Google Maps — live candidates, exact branch still needs your check.</p>
            <ul>{mapsResult.candidates.map(c => <li key={c.id}>
              <a href={c.googleMapsUri || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(c.displayName?.text || spot.name)}&query_place_id=${encodeURIComponent(c.id)}`} target="_blank" rel="noreferrer">{c.displayName?.text || c.id}</a>
              <p>{c.formattedAddress}</p>
            </li>)}</ul>
          </>}
        </div>}
        {(
          [
            ["name", "Location name"],
            ["area", "Neighbourhood"],
            ["address", "Exact address"],
            ["lat", "Latitude"],
            ["lng", "Longitude"],
            ["evidence_url", "Independent branch evidence URL"],
            ["maps_url", "Exact Google Maps place URL (full link with place ID or CID)"],
            ["reason", "What did you verify?"],
          ] as const
        ).map(([key, label]) => (
          <label key={key}>
            {label}
            <input
              required
              value={form[key]}
              type={
                key === "evidence_url" || key === "maps_url"
                  ? "url"
                  : key === "lat" || key === "lng"
                    ? "number"
                    : "text"
              }
              step="any"
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ))}
        <label>
          Category
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            required
            checked={form.checked}
            onChange={(e) => setForm({ ...form, checked: e.target.checked })}
          />{" "}
          I checked this exact branch and its map coordinates.
        </label>
        <label className="check-row">
          <input type="checkbox" required checked={form.maps_checked} onChange={e => setForm({ ...form, maps_checked: e.target.checked })} />
          I checked that this location name matches the exact Google Maps place.
        </label>
        <button className="primary" disabled={busy}>
          Save for final location approval
        </button>
      </form>
    </Modal>
  );
}

export default function IdentifiedSpots({
  onChanged,
}: {
  onChanged: () => void;
}) {
  const [spots, setSpots] = useState<Spot[] | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [selected, setSelected] = useState<Spot | null>(null);
  const [showHeld, setShowHeld] = useState(false), [held, setHeld] = useState(0);
  const [mergeSpot, setMergeSpot] = useState<Spot | null>(null);
  const [targetId, setTargetId] = useState(""), [mergeReason, setMergeReason] = useState(""), [mergeChecked, setMergeChecked] = useState(false);
  async function refresh() {
    try {
      const result = await api<{ spots: Spot[]; held: number }>(`/admin/spots?include_held=${showHeld}`);
      setSpots(result.spots);
      setHeld(result.held);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void refresh();
  }, [showHeld]);
  async function action(path: string) {
    setBusy(true);
    setError("");
    try {
      await post(path);
      await refresh();
      setMessage(
        path.endsWith("/collect")
          ? "First-party collection queued. Refresh after the worker finishes."
          : path.endsWith("/quality-check") ? "Duplicate and relevance checks completed. Originals remain in the held-record view." : "Investigation findings added to identified spots.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel identified-spots">
      <h2>Coimbatore identified spots</h2>
      <p>
        Maps, menus, activities and atmosphere evidence for the itinerary
        planner. Every location needs your approval before it can appear in
        suggestions.
      </p>
      <div className="inline-actions">
        <button
          className="secondary"
          disabled={busy}
          onClick={() => action("/admin/spots/sync-investigations")}
        >
          Add existing investigation findings
        </button>
        <button
          className="primary"
          disabled={busy}
          onClick={() => action("/admin/spots/collect")}
        >
          Collect official menus and details
        </button>
        <button className="secondary" onClick={() => void refresh()}>
          Refresh spots
        </button>
        <button className="secondary" disabled={busy} onClick={() => action("/admin/spots/quality-check")}>Check duplicates and relevance</button>
      </div>
      <label className="check-row"><input type="checkbox" checked={showHeld} onChange={e => setShowHeld(e.target.checked)} />Show held and merged records ({held})</label>
      <ErrorBox message={error} />
      {message && <p role="status">{message}</p>}
      {!spots ? (
        <Loading />
      ) : (
        <>
          <p>
            {spots.length} identified locations · drafts are not recommendations
          </p>
          <div className="review-grid">
            {spots.map((spot) => (
              <article className="review-card" key={spot.id}>
                <h3>{spot.name}</h3>
                <p className="small-text">{spot.data.maps_identity?.confirmed_by ? "Name and Maps branch checked by operator" : "Extracted name — Maps identity unconfirmed"}</p>
                {spot.data.aliases && spot.data.aliases.length > 1 && <p>Also seen as: {spot.data.aliases.join("; ")}</p>}
                {spot.data.quality_issues?.map(issue => <p key={issue}>{issue}</p>)}
                {spot.data.merged_into && <p>Merged into {spots.find(s => s.id === spot.data.merged_into)?.name || spot.data.merged_into}. Original evidence retained.</p>}
                {!!spot.data.possible_duplicates?.length && <p>Possible duplicate: {spot.data.possible_duplicates.map(id => spots.find(s => s.id === id)?.name || id).join("; ")}. Exact branch needs checking.</p>}
                <p>
                  {spot.area || "Neighbourhood unconfirmed"} · {spot.category} ·{" "}
                  {spot.status.replaceAll("_", " ")}
                </p>
                <p>{spot.data.address || "Exact address not yet confirmed."}</p>
                <p>{spot.data.hours || "Opening hours unknown."}</p>
                <div className="inline-actions">
                  <a
                    target="_blank"
                    rel="noreferrer"
                    href={spot.map_search_url}
                  >
                    Search this place on Maps
                  </a>
                  {spot.data.maps_links?.map((url, i) => (
                    <a key={url} href={url} target="_blank" rel="noreferrer">
                      Source map link {i + 1}
                    </a>
                  ))}
                </div>
                {spot.data.coordinates && (
                  <p className="small-text">
                    Map lead: {spot.data.coordinates.lat},{" "}
                    {spot.data.coordinates.lng}. {spot.data.coordinates.basis}
                  </p>
                )}
                <h4>Menu and activities</h4>
                {spot.data.menu_links?.map((url) => (
                  <p key={url}>
                    <a href={url} target="_blank" rel="noreferrer">
                      Open source menu
                    </a>
                  </p>
                ))}
                {spot.data.offerings?.length ? (
                  <details>
                    <summary>
                      {spot.data.offerings.length} collected items / activities
                    </summary>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Item</th>
                            <th>Listed price</th>
                            <th>Evidence</th>
                          </tr>
                        </thead>
                        <tbody>
                          {spot.data.offerings.map((item, i) => (
                            <tr key={i}>
                              <td>{item.name}</td>
                              <td>
                                {item.price_inr == null
                                  ? "Unknown"
                                  : `${money(item.price_inr)} / ${item.unit}`}
                              </td>
                              <td>
                                <a
                                  href={item.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  Source
                                </a>
                                <p className="small-text">{item.basis}</p>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                ) : (
                  <p>No menu items or activity prices collected yet.</p>
                )}
                <h4>Vibe evidence</h4>
                {spot.data.vibes?.length ? (
                  <ul>
                    {spot.data.vibes.map((v, i) => (
                      <li key={i}>
                        {v.tag}: {v.evidence || v.basis}{" "}
                        <a href={v.source_url} target="_blank" rel="noreferrer">
                          Source
                        </a>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Atmosphere unknown; it has not been guessed.</p>
                )}
                <details>
                  <summary>
                    Sources and collection dates (
                    {spot.data.sources?.length || 0})
                  </summary>
                  <ul>
                    {spot.data.sources?.map((s, i) => (
                      <li key={i}>
                        <a href={s.url} target="_blank" rel="noreferrer">
                          {s.type} source
                        </a>{" "}
                        ·{" "}
                        {s.published_at
                          ? `Published ${dateText(s.published_at)}`
                          : "Publication date unknown"}{" "}
                        · Collected {dateText(s.collected_at)}
                        <p>{s.basis}</p>
                      </li>
                    ))}
                  </ul>
                </details>
                <p className="small-text">
                  Missing:{" "}
                  {spot.missing.join("; ") ||
                    "Check all collected details before approval."}
                </p>
                {spot.status === "merged" ? null : spot.venue_id ? (
                  <p>
                    Continue fact review and location approval in Venue desk.
                  </p>
                ) : (
                  <button
                    className="secondary"
                    onClick={() => setSelected(spot)}
                  >
                    Prepare location for approval
                  </button>
                )}
                {!spot.venue_id && !["merged", "quarantined", "rejected"].includes(spot.status) && <button className="secondary" onClick={() => { setMergeSpot(spot); setTargetId(""); setMergeReason(""); setMergeChecked(false); }}>Merge duplicate after branch check</button>}
              </article>
            ))}
          </div>
        </>
      )}
      {selected && (
        <Prepare
          spot={selected}
          close={() => setSelected(null)}
          saved={() => {
            void refresh();
            onChanged();
          }}
        />
      )}
      {mergeSpot && <Modal title={`Merge ${mergeSpot.name}`} onClose={() => setMergeSpot(null)}>
        <form className="stack-form" onSubmit={async e => {
          e.preventDefault(); setBusy(true); setError("");
          try { await post(`/admin/spots/${mergeSpot.id}/merge`, { target_id: targetId, reason: mergeReason, same_branch_checked: mergeChecked }); setMergeSpot(null); await refresh(); }
          catch (e) { setError((e as Error).message); }
          finally { setBusy(false); }
        }}>
          <p>Keep all source evidence in the surviving record. Check the address: different branches must stay separate.</p>
          <ErrorBox message={error} />
          <label>Surviving location<select required value={targetId} onChange={e => setTargetId(e.target.value)}><option value="">Choose a location</option>{spots?.filter(s => s.id !== mergeSpot.id && !s.venue_id && !["merged", "quarantined", "rejected"].includes(s.status)).map(s => <option key={s.id} value={s.id}>{s.name} — {s.area || "area unknown"}</option>)}</select></label>
          <label>Evidence for the same branch<input required minLength={10} value={mergeReason} onChange={e => setMergeReason(e.target.value)} /></label>
          <label className="check-row"><input required type="checkbox" checked={mergeChecked} onChange={e => setMergeChecked(e.target.checked)} />I checked that both records refer to the same branch.</label>
          <button className="primary" disabled={busy}>Merge and retain original evidence</button>
        </form>
      </Modal>}
    </section>
  );
}
