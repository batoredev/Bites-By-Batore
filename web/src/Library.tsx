import { useEffect, useState, type FormEvent } from "react";
import { DownloadSimple, Trash, ArrowRight } from "@phosphor-icons/react";
import { api } from "./api";
import {
  PageTitle,
  Empty,
  ErrorBox,
  VenueCard,
  PlanCard,
  Loading,
} from "./components";
import type { Venue, Plan, User, Visit, Profile } from "./types";
import DishDiary from "./DishDiary";
import VisitHistory from "./VisitHistory";

export { default as Places } from "./ExplorePlaces";

export function Saved({
  venues,
  onVenue,
  onSaveVenue,
  onPlan,
  onSavePlan,
  revision,
}: {
  venues: Venue[];
  onVenue: (v: Venue) => void;
  onSaveVenue: (v: Venue) => void;
  onPlan: (p: Plan) => void;
  onSavePlan: (p: Plan) => void;
  revision: number;
}) {
  const [plans, setPlans] = useState<Plan[]>([]),
    [savedPlaces, setSavedPlaces] = useState<Venue[]>(
      venues.filter((v) => v.saved),
    ),
    [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [tab, setTab] = useState("plans");
  useEffect(() => {
    setBusy(true);
    setError("");
    Promise.all([api<Plan[]>("/plans"), api<Venue[]>("/me/saved-venues")])
      .then(([foundPlans, foundPlaces]) => {
        setPlans(foundPlans);
        setSavedPlaces(foundPlaces);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, [revision]);
  return (
    <>
      <PageTitle
        eyebrow="FOR ANOTHER GOOD DAY"
        title="Your little collection."
        description="Plans worth keeping and places you want to come back to."
      />
      <div className="tabs" role="group" aria-label="Collection views">
        <button
          className={tab === "plans" ? "active" : ""}
          aria-pressed={tab === "plans"}
          onClick={() => setTab("plans")}
        >
          Saved plans <span>{plans.length}</span>
        </button>
        <button
          className={tab === "places" ? "active" : ""}
          aria-pressed={tab === "places"}
          onClick={() => setTab("places")}
        >
          Saved places <span>{savedPlaces.length}</span>
        </button>
      </div>
      <ErrorBox message={error} />
      {busy ? (
        <Loading label="Opening your collection…" />
      ) : tab === "plans" ? (
        plans.length ? (
          <div className="plan-grid">
            {plans.map((p, i) => (
              <div key={p.id}>
                {p.needs_refresh && (
                  <p className="notice small-text">
                    Recheck before heading out
                  </p>
                )}
                <PlanCard
                  plan={p}
                  index={i}
                  onOpen={() => onPlan(p)}
                  onSave={() => onSavePlan(p)}
                />
              </div>
            ))}
          </div>
        ) : (
          <Empty title="Make room for a good plan">
            Tap the bookmark on an outing to keep it here. Saved plans can be
            rechecked when you’re ready.
          </Empty>
        )
      ) : savedPlaces.length ? (
        <div className="venue-grid">
          {savedPlaces.map((v) => (
            <VenueCard
              key={v.id}
              venue={v}
              onOpen={() => onVenue(v)}
              onSave={() => onSaveVenue(v)}
            />
          ))}
        </div>
      ) : (
        <Empty title="Your next favourite is out there">
          Bookmark a place while exploring and it will appear here.
        </Empty>
      )}
    </>
  );
}

export function Taste({
  user,
  onUpdate,
  venues,
}: {
  user: User;
  onUpdate: () => void;
  venues: Venue[];
}) {
  const [name, setName] = useState(user.name),
    [liked, setLiked] = useState((user.profile.liked_tags || []).join(", ")),
    [avoided, setAvoided] = useState(
      (user.profile.avoided_tags || []).join(", "),
    ),
    [cuisines, setCuisines] = useState(
      (user.profile.preferred_cuisines || []).join(", "),
    ),
    [profile, setProfile] = useState<Profile>(user.profile),
    [visits, setVisits] = useState<Visit[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [erase, setErase] = useState("");
  useEffect(() => {
    api<Visit[]>("/visits")
      .then(setVisits)
      .catch((e) => setError(e.message));
  }, [user]);
  useEffect(() => {
    setProfile(user.profile);
    setLiked((user.profile.liked_tags || []).join(", "));
    setAvoided((user.profile.avoided_tags || []).join(", "));
    setCuisines((user.profile.preferred_cuisines || []).join(", "));
  }, [user]);
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/me", {
        method: "PUT",
        body: JSON.stringify({
          name,
          liked_tags: liked
            .split(",")
            .map((s) => s.trim().toLowerCase())
            .filter(Boolean),
          avoided_tags: avoided
            .split(",")
            .map((s) => s.trim().toLowerCase())
            .filter(Boolean),
          vegetarian: !!profile.vegetarian,
          wheelchair: !!profile.wheelchair,
          learn_from_visits: profile.learn_from_visits !== false,
          preferred_cuisines: cuisines
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          spice_preference: profile.spice_preference || "any",
        }),
      });
      setMessage("Your preferences are saved.");
      onUpdate();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function clear(all = false) {
    setError("");
    try {
      await api(all ? "/me/data" : "/me/memory", { method: "DELETE" });
      setMessage(
        all
          ? "Private application data erased."
          : "Taste memory and visits cleared.",
      );
      setErase("");
      onUpdate();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function download() {
    try {
      const data = await api("/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "my-batore-data.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="LESS GUESSWORK, MORE YOU"
        title="A taste of who you are."
        description="Tell us what you like. Keep, change or clear what the app learns."
      />
      <nav className="section-shortcuts" aria-label="Taste sections">
        <a href="#preferences">Preferences</a>
        <a href="#dish-diary">Dish diary</a>
        <a href="#visit-history">Visit history</a>
        <a href="#privacy">Privacy & data</a>
      </nav>
      <div className="profile-grid">
        <form
          className="panel stack-form preference-form"
          id="preferences"
          onSubmit={save}
        >
          <h2>Your preferences</h2>
          <label>
            What should we call you?
            <input
              required
              maxLength={60}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Things you love <small>Separate with commas</small>
            <input
              value={liked}
              onChange={(e) => setLiked(e.target.value)}
              placeholder="sushi, coffee, bowling, quiet"
            />
          </label>
          <label>
            Things to avoid
            <input
              value={avoided}
              onChange={(e) => setAvoided(e.target.value)}
              placeholder="spicy, outdoor"
            />
          </label>
          <label>
            Preferred cuisines <small>Separate with commas</small>
            <input
              value={cuisines}
              onChange={(e) => setCuisines(e.target.value)}
              placeholder="Japanese, South Indian"
            />
          </label>
          <label>
            Preferred spice level
            <select
              value={profile.spice_preference || "any"}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  spice_preference: e.target
                    .value as Profile["spice_preference"],
                })
              }
            >
              <option value="any">No preference</option>
              <option value="mild">Mild</option>
              <option value="medium">Medium</option>
              <option value="hot">Hot</option>
            </select>
          </label>
          <div className="checks vertical">
            <label>
              <input
                type="checkbox"
                checked={!!profile.vegetarian}
                onChange={(e) =>
                  setProfile({ ...profile, vegetarian: e.target.checked })
                }
              />
              Vegetarian options required
            </label>
            <label>
              <input
                type="checkbox"
                checked={!!profile.wheelchair}
                onChange={(e) =>
                  setProfile({ ...profile, wheelchair: e.target.checked })
                }
              />
              Step-free access required
            </label>
            <label>
              <input
                type="checkbox"
                checked={profile.learn_from_visits !== false}
                onChange={(e) =>
                  setProfile({
                    ...profile,
                    learn_from_visits: e.target.checked,
                  })
                }
              />
              Learn from my visit and dish feedback
            </label>
          </div>
          <button className="primary" disabled={busy}>
            {busy ? "Saving…" : "Save preferences"}
            <ArrowRight />
          </button>
        </form>
        <div>
          <section className="panel">
            <div className="eyebrow">LEARNED, NOT ASSUMED</div>
            <h2>Your emerging interests</h2>
            <p className="muted">
              These signals come from your visit scores and dishes marked as
              favourites or not for you. Saved places and dishes to try do not
              count as visits or taste feedback.
            </p>
            {Object.entries(user.profile.inferred || {}).length ? (
              <div className="inference-list">
                {Object.entries(user.profile.inferred || {}).map(
                  ([tag, score]) => (
                    <div key={tag}>
                      <span>{tag}</span>
                      <span className={score > 0 ? "green" : "muted"}>
                        {score > 0
                          ? "Leaning toward"
                          : score < 0
                            ? "Less interested"
                            : "Neutral"}
                      </span>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <p className="empty-inline">
                A fresh start. No inferred interests yet.
              </p>
            )}
            <p className="small-text muted">
              Your current budget is always your choice. Feedback never raises
              it.
            </p>
          </section>
          <section className="panel privacy-panel" id="privacy">
            <h3>Your memory, your control</h3>
            <button className="text-button" onClick={download}>
              <DownloadSimple />
              Export my app data
            </button>
            <button className="text-button" onClick={() => setErase("memory")}>
              <Trash />
              Clear taste memory & visits
            </button>
            <button
              className="text-button danger"
              onClick={() => setErase("all")}
            >
              <Trash />
              Erase all private app data
            </button>
            {erase && (
              <div className="notice">
                <p>
                  {erase === "all"
                    ? "This erases your saved plans, saved places, submissions and taste history. Your sign-in remains."
                    : "This clears preferences, confirmed visits and your dish diary. Saved places and plans stay."}
                </p>
                <button
                  className="danger-button"
                  onClick={() => clear(erase === "all")}
                >
                  Confirm erase
                </button>
                <button className="text-button" onClick={() => setErase("")}>
                  Cancel
                </button>
              </div>
            )}
          </section>
        </div>
      </div>
      <ErrorBox message={error} />
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
      <DishDiary changed={onUpdate} />
      <section id="visit-history" className="visit-history">
        <div className="section-heading">
          <h2>The places you’ve been.</h2>
          <span className="muted">Only visits you recorded</span>
        </div>
        {visits.length ? (
          <div className="visit-list">
            {visits.map((v) => (
              <VisitHistory
                key={v.id}
                visit={v}
                venueName={
                  v.experience?.venue_name ||
                  venues.find((p) => p.id === v.venue_id)?.name ||
                  "Venue"
                }
                changed={onUpdate}
              />
            ))}
          </div>
        ) : (
          <Empty title="Your story starts with a visit">
            Open a place and choose “I visited” to tell us how it went.
          </Empty>
        )}
      </section>
    </>
  );
}
