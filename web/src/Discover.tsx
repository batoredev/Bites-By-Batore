import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  Compass,
  SlidersHorizontal,
  MapPin,
  Sparkle,
  NavigationArrow,
} from "@phosphor-icons/react";
import { post } from "./api";
import DiscoveryGuide from "./DiscoveryGuide";
import {
  categories,
  ErrorBox,
  Loading,
  PlanCard,
  VenueCard,
} from "./components";
import type { OutingRequest, Plan, PlanResponse, User, Venue } from "./types";

export function defaultRequest(user: User): OutingRequest {
  const day = new Date(Date.now() + 86400000).toLocaleDateString("en-CA", {
    timeZone: "Asia/Kolkata",
  });
  return {
    query: "",
    start_label: "RS Puram, Coimbatore",
    lat: 11.008,
    lng: 76.948,
    duration_minutes: 180,
    party_size: 2,
    budget: 2400,
    budget_unit: "group",
    departure: `${day}T17:00:00+05:30`,
    transport: "drive",
    categories: categories.map((c) => c.id),
    outing_type: "any",
    mood: "different",
    vegetarian: !!user.profile.vegetarian,
    wheelchair: !!user.profile.wheelchair,
    children: false,
    avoid_tags: [],
    companion_interests: [],
    exclude_ids: [],
    lock_ids: [],
  };
}
const starts = [
  ["RS Puram, Coimbatore", 11.008, 76.948],
  ["Gandhipuram, Coimbatore", 11.017, 76.967],
  ["Race Course, Coimbatore", 10.998, 76.977],
  ["Saibaba Colony, Coimbatore", 11.029, 76.95],
  ["Peelamedu, Coimbatore", 11.025, 77.004],
] as const;
export default function Discover({
  venues,
  onVenue,
  onSaveVenue,
  onPlan,
  onSavePlan,
  plans,
  setPlans,
  request,
  setRequest,
}: {
  user: User;
  venues: Venue[];
  onVenue: (v: Venue) => void;
  onSaveVenue: (v: Venue) => void;
  onPlan: (p: Plan) => void;
  onSavePlan: (p: Plan) => void;
  plans: Plan[];
  setPlans: (p: Plan[]) => void;
  request: OutingRequest;
  setRequest: (r: OutingRequest) => void;
}) {
  const [visiblePlans, setVisiblePlans] = useState(24);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [response, setResponse] = useState<PlanResponse | null>(
      plans.length
        ? {
            options: plans,
            excluded: {},
            message: "Your revised options are ready.",
            candidate_count: 0,
          }
        : null,
    ),
    [advanced, setAdvanced] = useState(false),
    [custom, setCustom] = useState(false);
  const change = <K extends keyof OutingRequest>(
    key: K,
    value: OutingRequest[K],
  ) => setRequest({ ...request, [key]: value });
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setPlans([]);
    setResponse(null);
    try {
      const r = await post<PlanResponse>("/plans", {
        ...request,
        query: request.query || "Something different",
        exclude_ids: [],
        lock_ids: [],
        // Ask for every distinct plan the server will return, best first.
        max_options: 400,
      });
      setPlans(r.options);
      setVisiblePlans(24);
      setResponse(r);
      setTimeout(
        () =>
          document
            .getElementById("results")
            ?.scrollIntoView({ behavior: "smooth", block: "start" }),
        50,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function locate() {
    if (!navigator.geolocation) {
      setError("Location sharing is unavailable. Enter coordinates instead.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setRequest({
          ...request,
          start_label: "My shared location",
          lat: p.coords.latitude,
          lng: p.coords.longitude,
        });
        setCustom(true);
      },
      () =>
        setError(
          "Could not read your location. Choose an area or enter coordinates.",
        ),
      { timeout: 10000 },
    );
  }
  return (
    <>
      <section className="discover-hero">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="little-line" />A LITTLE MORE LOCAL
          </div>
          <h1>
            Your next good plan
            <span>
              starts <em>here.</em>
            </span>
          </h1>
          <p>
            Find a little food, a little play, or both — in the time and budget
            you have.
          </p>
          <div className="hero-footnote">
            <Compass size={18} />
            <span>Made for your taste, time & budget</span>
          </div>
        </div>
        <div className="city-callout">
          <Compass size={32} weight="duotone" />
          <span>
            COIMBATORE, AT YOUR PACE
            <strong>
              A few hours.
              <br />A good change of scene.
            </strong>
          </span>
        </div>
      </section>
      <form className="planner-form" onSubmit={submit}>
        <div className="form-intro">
          <h2>Start with a craving or a feeling.</h2>
          <span>No idea is a good starting point.</span>
        </div>
        <label className="query-field">
          <Sparkle size={24} />
          <input
            aria-label="What would you like to do?"
            value={request.query}
            maxLength={500}
            onChange={(e) => change("query", e.target.value)}
            placeholder="Sushi with friends, or just something different…"
          />
        </label>
        <div className="mood-row">
          {[
            { id: "different", label: "Surprise me" },
            { id: "comfort", label: "Something familiar" },
            { id: "quiet", label: "Slow & quiet" },
            { id: "social", label: "Time with friends" },
            { id: "active", label: "A little adventure" },
          ].map((m) => (
            <button
              type="button"
              key={m.id}
              className={`chip ${request.mood === m.id ? "active" : ""}`}
              aria-pressed={request.mood === m.id}
              onClick={() => change("mood", m.id as OutingRequest["mood"])}
            >
              {m.label}
            </button>
          ))}
        </div>
        <div className="discovery-options">
          <label className="novelty-control">
            How different should it feel?
            <select
              value={
                request.novelty ||
                (request.mood === "different" ? "new_place" : "familiar")
              }
              onChange={(e) =>
                change("novelty", e.target.value as OutingRequest["novelty"])
              }
            >
              <option value="new_place">
                A new place, familiar tastes welcome
              </option>
              <option value="new_taste">Explore beyond my usual tastes</option>
              <option value="familiar">Familiar favourites</option>
            </select>
          </label>
          <DiscoveryGuide request={request} apply={setRequest} />
        </div>
        <div className="planner-section-label">
          <MapPin size={18} />
          <h3>Make it fit your day</h3>
          <span>Travel and stops share your time.</span>
        </div>
        <div className="parameter-grid">
          <label>
            Starting from
            <select
              value={custom ? "custom" : request.start_label}
              onChange={(e) => {
                const p = starts.find((s) => s[0] === e.target.value);
                if (p) {
                  setCustom(false);
                  setRequest({
                    ...request,
                    start_label: p[0],
                    lat: p[1],
                    lng: p[2],
                  });
                } else setCustom(true);
              }}
            >
              {starts.map((s) => (
                <option key={s[0]} value={s[0]}>
                  {s[0].replace(", Coimbatore", "")}
                </option>
              ))}
              <option value="custom">My location / coordinates</option>
            </select>
          </label>
          <label>
            Time to spend
            <select
              value={request.duration_minutes}
              onChange={(e) => change("duration_minutes", +e.target.value)}
            >
              {[60, 90, 120, 180, 240, 360, 480, 720].map((n) => (
                <option value={n} key={n}>
                  {n / 60} hours
                </option>
              ))}
            </select>
          </label>
          <label>
            People
            <input
              type="number"
              min="1"
              max="20"
              required
              value={request.party_size}
              onChange={(e) => change("party_size", +e.target.value)}
            />
          </label>
          <label>
            Budget · INR
            <div className="budget-input">
              <input
                aria-label="Budget in rupees"
                type="number"
                min="50"
                max="100000"
                required
                value={request.budget}
                onChange={(e) => change("budget", +e.target.value)}
              />
              <select
                aria-label="Budget applies to"
                value={request.budget_unit}
                onChange={(e) =>
                  change("budget_unit", e.target.value as "group" | "person")
                }
              >
                <option value="group">total</option>
                <option value="person">each</option>
              </select>
            </div>
          </label>
        </div>
        {custom && (
          <div className="custom-location">
            <button className="secondary" type="button" onClick={locate}>
              <NavigationArrow />
              Use my location
            </button>
            <label>
              Location label
              <input
                required
                value={request.start_label}
                onChange={(e) => change("start_label", e.target.value)}
              />
            </label>
            <label>
              Latitude
              <input
                type="number"
                step="any"
                min="-90"
                max="90"
                required
                value={request.lat}
                onChange={(e) => change("lat", +e.target.value)}
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                step="any"
                min="-180"
                max="180"
                required
                value={request.lng}
                onChange={(e) => change("lng", +e.target.value)}
              />
            </label>
          </div>
        )}
        <div className="parameter-grid secondary-parameters">
          <label>
            Departure · India time
            <input
              type="datetime-local"
              required
              value={request.departure.slice(0, 16)}
              onChange={(e) =>
                change("departure", e.target.value + ":00+05:30")
              }
            />
          </label>
          <label>
            Getting around
            <select
              value={request.transport}
              onChange={(e) =>
                change(
                  "transport",
                  e.target.value as OutingRequest["transport"],
                )
              }
            >
              <option value="drive">Car</option>
              <option value="walk">Walking</option>
              <option value="taxi">Taxi</option>
              <option value="bike">Motorbike</option>
            </select>
          </label>
          <label>
            Kind of plan
            <select
              value={request.outing_type}
              onChange={(e) =>
                change(
                  "outing_type",
                  e.target.value as OutingRequest["outing_type"],
                )
              }
            >
              <option value="any">Any outing</option>
              <option value="food">Food & cafés</option>
              <option value="entertainment">Entertainment</option>
              <option value="combined">Food + entertainment</option>
            </select>
          </label>
          <button
            className={`secondary more-button ${advanced ? "active" : ""}`}
            type="button"
            aria-expanded={advanced}
            onClick={() => setAdvanced(!advanced)}
          >
            <SlidersHorizontal />
            Fine-tune my plan
          </button>
        </div>
        {advanced && (
          <div className="advanced">
            <div className="two-col">
              <label>
                Maximum stops
                <select
                  value={request.max_stops || 2}
                  onChange={(e) => change("max_stops", +e.target.value)}
                >
                  {[1, 2, 3, 4].map((n) => (
                    <option key={n} value={n}>
                      {n} {n === 1 ? "stop" : "stops"}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Occasion
                <select
                  value={request.occasion || "casual"}
                  onChange={(e) => change("occasion", e.target.value)}
                >
                  {["casual", "friends", "family", "date", "solo"].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="label">Include these places</div>
            <div className="category-row">
              {categories.map((c) => (
                <button
                  type="button"
                  className={`chip ${request.categories.includes(c.id) ? "active" : ""}`}
                  key={c.id}
                  aria-pressed={request.categories.includes(c.id)}
                  onClick={() =>
                    change(
                      "categories",
                      request.categories.includes(c.id)
                        ? request.categories.filter((x) => x !== c.id)
                        : [...request.categories, c.id],
                    )
                  }
                >
                  <c.icon />
                  {c.label}
                </button>
              ))}
            </div>
            <div className="checks">
              <label>
                <input
                  type="checkbox"
                  checked={request.vegetarian}
                  onChange={(e) => change("vegetarian", e.target.checked)}
                />
                Vegetarian options required
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={request.wheelchair}
                  onChange={(e) => change("wheelchair", e.target.checked)}
                />
                Step-free access required
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={request.children}
                  onChange={(e) => change("children", e.target.checked)}
                />
                Children joining
              </label>
            </div>
            <div className="two-col">
              <label>
                Companion interests <small>Separate with commas</small>
                <input
                  placeholder="coffee, bowling, quiet"
                  value={request.companion_interests.join(", ")}
                  onChange={(e) =>
                    change(
                      "companion_interests",
                      e.target.value
                        .split(",")
                        .map((s) => s.trim().toLowerCase()),
                    )
                  }
                />
              </label>
              <label>
                Individual companion preferences{" "}
                <small>One person per line; comma-separated interests</small>
                <textarea
                  value={(request.companion_preferences || [])
                    .map((x) => x.join(", "))
                    .join("\n")}
                  onChange={(e) =>
                    change(
                      "companion_preferences",
                      e.target.value
                        .split("\n")
                        .map((line) =>
                          line.split(",").map((x) => x.trim().toLowerCase()),
                        )
                        .filter((line) => line.some(Boolean)),
                    )
                  }
                />
              </label>
              <label>
                Avoid for this outing
                <input
                  placeholder="spicy, outdoor"
                  value={request.avoid_tags.join(", ")}
                  onChange={(e) =>
                    change(
                      "avoid_tags",
                      e.target.value
                        .split(",")
                        .map((s) => s.trim().toLowerCase()),
                    )
                  }
                />
              </label>
            </div>
            <p className="muted small-text">
              Dietary tags describe available options, not allergen guarantees.
              Transport expenses and waiting times are estimates.
            </p>
          </div>
        )}
        <ErrorBox message={error} />
        <div className="form-bottom">
          <span>
            <MapPin size={16} />
            Your time includes travel and stops, ending at the last place.
          </span>
          <button
            className="primary"
            disabled={busy || !request.categories.length}
          >
            {busy ? "Putting it together…" : "Find my plan"}
            <ArrowRight size={20} />
          </button>
        </div>
      </form>
      <section id="results" aria-live="polite">
        {busy && <Loading />}
        {response && (
          <>
            <div className="section-heading">
              <div>
                <div className="eyebrow">BUILT AROUND YOU</div>
                <h2>
                  {plans.length
                    ? plans.length === 1
                      ? "One plan fits."
                      : `${plans.length} plans fit, best first.`
                    : "Let’s adjust the plan."}
                </h2>
              </div>
              <span className="muted">
                {response.candidate_count} eligible places considered
              </span>
            </div>
            <p className="muted">
              {response.message}
              {(response.total_options || 0) > plans.length &&
                ` Showing the best ${plans.length} of ${response.total_options} possible combinations.`}
            </p>
            {response.investigation_id && (
              <p className="notice">
                We started an investigation for this request.{" "}
                <a href="/sources">Follow its evidence checks</a> before trying
                a fresh plan.
              </p>
            )}
            {plans.length > 0 && (
              <div className="plan-grid">
                {plans.slice(0, visiblePlans).map((p, i) => (
                  <PlanCard
                    key={p.id}
                    plan={p}
                    index={i}
                    onOpen={() => onPlan(p)}
                    onSave={() => onSavePlan(p)}
                  />
                ))}
              </div>
            )}
            {plans.length > visiblePlans && (
              <div className="form-bottom">
                <span>
                  Showing {visiblePlans} of {plans.length} plans, best first.
                </span>
                <button
                  className="secondary"
                  onClick={() => setVisiblePlans(visiblePlans + 24)}
                >
                  Show 24 more
                </button>
                <button
                  className="secondary"
                  onClick={() => setVisiblePlans(plans.length)}
                >
                  Show all {plans.length}
                </button>
              </div>
            )}
            {Object.keys(response.excluded).length > 0 && (
              <details className="exclusions">
                <summary>What affected these options?</summary>
                <p>
                  Some venues or possible combinations were excluded for:{" "}
                  {Object.keys(response.excluded).join(", ")}. Counts can
                  overlap because several combinations are checked.
                </p>
              </details>
            )}
          </>
        )}
      </section>
      <section>
        <div className="section-heading">
          <div>
            <div className="eyebrow">A FEW STARTING POINTS</div>
            <h2>Follow your curiosity.</h2>
          </div>
          <span className="muted">
            {venues[0]?.is_demo
              ? "Fictional places to try the app"
              : "Places in your city"}
          </span>
        </div>
        <div className="venue-grid">
          {venues.slice(0, 3).map((v) => (
            <VenueCard
              key={v.id}
              venue={v}
              onOpen={() => onVenue(v)}
              onSave={() => onSaveVenue(v)}
            />
          ))}
        </div>
      </section>
    </>
  );
}
