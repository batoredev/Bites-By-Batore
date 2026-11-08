import { useEffect, useRef, useState } from "react";
import { MagnifyingGlass, SlidersHorizontal } from "@phosphor-icons/react";
import { api } from "./api";
import {
  categories,
  PageTitle,
  Empty,
  ErrorBox,
  Loading,
  VenueCard,
} from "./components";
import type { Venue } from "./types";

export default function ExplorePlaces({
  venues,
  onVenue,
  onSave,
}: {
  venues: Venue[];
  onVenue: (v: Venue) => void;
  onSave: (v: Venue) => void;
}) {
  const [category, setCategory] = useState("all"),
    [q, setQ] = useState(""),
    [area, setArea] = useState(""),
    [cuisine, setCuisine] = useState(""),
    [format, setFormat] = useState(""),
    [price, setPrice] = useState("");
  const [vegetarian, setVegetarian] = useState(false),
    [parking, setParking] = useState(false),
    [washroom, setWashroom] = useState(false);
  const [rows, setRows] = useState<Venue[]>(venues),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [more, setMore] = useState(false);
  const [retry, setRetry] = useState(0);
  const activeFilters = [
    category !== "all",
    !!q,
    !!area,
    !!cuisine,
    !!format,
    !!price,
    vegetarian,
    parking,
    washroom,
  ].filter(Boolean).length;
  function clearFilters() {
    setQ("");
    setCategory("all");
    setArea("");
    setCuisine("");
    setFormat("");
    setPrice("");
    setVegetarian(false);
    setParking(false);
    setWashroom(false);
  }
  const params = new URLSearchParams({
    q,
    area,
    cuisine,
    dining_format: format,
    limit: "60",
  });
  if (category !== "all") params.set("category", category);
  if (price && Number.isFinite(Number(price)) && Number(price) >= 0)
    params.set("max_price", price);
  if (vegetarian) params.set("vegetarian", "true");
  if (parking) params.set("parking", "true");
  if (washroom) params.set("washroom", "true");
  const query = params.toString();
  const latest = useRef(query);
  latest.current = query;
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError("");
    setRows([]);
    setMore(false);
    const timer = setTimeout(() => {
      setBusy(true);
      setError("");
      api<Venue[]>(`/venues?${query}`)
        .then((found) => {
          if (active) {
            setRows(found);
            setMore(found.length === 60);
          }
        })
        .catch((e) => {
          if (active) {
            setError(e.message);
            setRows([]);
          }
        })
        .finally(() => {
          if (active) setBusy(false);
        });
    }, 180);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query, retry]);
  useEffect(() => {
    setRows((previous) =>
      previous.map((row) => venues.find((v) => v.id === row.id) || row),
    );
  }, [venues]);
  async function loadMore() {
    setBusy(true);
    setError("");
    const expected = query;
    try {
      const found = await api<Venue[]>(
        `/venues?${query}&offset=${rows.length}`,
      );
      if (latest.current === expected) {
        setRows((previous) => [
          ...previous,
          ...found.filter((v) => !previous.some((p) => p.id === v.id)),
        ]);
        setMore(found.length === 60);
      }
    } catch (e) {
      if (latest.current === expected) setError((e as Error).message);
    } finally {
      if (latest.current === expected) setBusy(false);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="YOUR CITY, A LITTLE CLOSER"
        title="Good places. More possibilities."
        description="Explore reviewed dishes, cuisines, places and practical details."
      />
      <label className="search-box">
        <MagnifyingGlass size={20} />
        <input
          aria-label="Search places"
          value={q}
          maxLength={150}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search a dish, place, cuisine or neighbourhood…"
        />
      </label>
      <div className="category-row browse-categories">
        <button
          className={`chip ${category === "all" ? "active" : ""}`}
          aria-pressed={category === "all"}
          onClick={() => setCategory("all")}
        >
          Everything
        </button>
        {categories.map((c) => (
          <button
            key={c.id}
            className={`chip ${category === c.id ? "active" : ""}`}
            aria-pressed={category === c.id}
            onClick={() => setCategory(c.id)}
          >
            <c.icon />
            {c.label}
          </button>
        ))}
      </div>
      <details className="panel explore-filters">
        <summary>
          <SlidersHorizontal size={19} />
          <span>Filter by cuisine, area and practical details</span>
          {activeFilters > 0 && (
            <span className="filter-count" aria-hidden="true">
              {activeFilters}
            </span>
          )}
        </summary>
        <div className="parameter-grid">
          <label>
            Area
            <input
              value={area}
              maxLength={100}
              onChange={(e) => setArea(e.target.value)}
              placeholder="Any Coimbatore area"
            />
          </label>
          <label>
            Cuisine
            <input
              value={cuisine}
              maxLength={100}
              onChange={(e) => setCuisine(e.target.value)}
              placeholder="Any reviewed cuisine"
            />
          </label>
          <label>
            Dining format
            <select value={format} onChange={(e) => setFormat(e.target.value)}>
              <option value="">Any reviewed format</option>
              {[
                "cafe",
                "casual_dining",
                "fine_dining",
                "quick_service",
                "street_food",
                "food_court",
                "bakery",
                "dessert_shop",
              ].map((f) => (
                <option value={f} key={f}>
                  {f.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Maximum listed dish price (INR)
            <input
              type="number"
              min="0"
              max="100000"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="No limit"
            />
          </label>
        </div>
        <div className="checks">
          <label>
            <input
              type="checkbox"
              checked={vegetarian}
              onChange={(e) => setVegetarian(e.target.checked)}
            />
            Reviewed vegetarian dish required
          </label>
          <label>
            <input
              type="checkbox"
              checked={parking}
              onChange={(e) => setParking(e.target.checked)}
            />
            Confirmed parking
          </label>
          <label>
            <input
              type="checkbox"
              checked={washroom}
              onChange={(e) => setWashroom(e.target.checked)}
            />
            Confirmed washroom
          </label>
        </div>
        <p className="small-text muted">
          Unknown or expired evidence does not satisfy these filters. Listed
          dish prices are separate from the total outing budget.
        </p>
        <button type="button" className="text-button" onClick={clearFilters}>
          Clear filters
        </button>
      </details>
      <p className="muted small-text" role="status">
        {busy ? "Checking matching places…" : `Showing ${rows.length} places`} ·{" "}
        {venues[0]?.is_demo
          ? "Fictional inventory for demonstration"
          : "Approved venue records"}
      </p>
      <ErrorBox message={error} />
      {error && (
        <button className="secondary" onClick={() => setRetry((n) => n + 1)}>
          Retry search
        </button>
      )}
      <div aria-busy={busy}>
        {busy && !rows.length ? (
          <Loading label="Finding matching places…" />
        ) : rows.length ? (
          <div className="venue-grid">
            {rows.map((v) => (
              <VenueCard
                key={v.id}
                venue={v}
                onOpen={() => onVenue(v)}
                onSave={() => onSave(v)}
              />
            ))}
          </div>
        ) : (
          !busy &&
          !error && (
            <Empty title="Nothing here yet">
              Try another category or search. Real locations need approval, and
              unknown facts cannot satisfy the selected filters.
            </Empty>
          )
        )}
      </div>
      {!busy && !error && !rows.length && activeFilters > 0 && (
        <button className="secondary" onClick={clearFilters}>
          Reset search and filters
        </button>
      )}
      {more && (
        <button className="secondary" disabled={busy} onClick={loadMore}>
          Load more places
        </button>
      )}
    </>
  );
}
