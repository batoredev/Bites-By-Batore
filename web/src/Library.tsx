import { useEffect, useState, type FormEvent } from "react";
import {
  DownloadSimple,
  Trash,
  MagnifyingGlass,
  ArrowRight,
} from "@phosphor-icons/react";
import { api } from "./api";
import {
  categories,
  PageTitle,
  Empty,
  ErrorBox,
  VenueCard,
  PlanCard,
  Loading,
} from "./components";
import type { Venue, Plan, User, Visit, Profile } from "./types";

export function Places({
  venues,
  onVenue,
  onSave,
}: {
  venues: Venue[];
  onVenue: (v: Venue) => void;
  onSave: (v: Venue) => void;
}) {
  const [category, setCategory] = useState("all"),
    [q, setQ] = useState("");
  const rows = venues.filter(
    (v) =>
      (category === "all" || v.category === category) &&
      `${v.name} ${v.area} ${v.tags.join(" ")}`
        .toLowerCase()
        .includes(q.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        eyebrow="YOUR CITY, A LITTLE CLOSER"
        title="Good places. More possibilities."
        description="Explore by flavour, activity or the kind of day you want."
      />
      <label className="search-box">
        <MagnifyingGlass size={20} />
        <input
          aria-label="Search places"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search sushi, coffee, bowling, a neighbourhood…"
        />
      </label>
      <div className="category-row browse-categories">
        <button
          className={`chip ${category === "all" ? "active" : ""}`}
          onClick={() => setCategory("all")}
        >
          Everything
        </button>
        {categories.map((c) => (
          <button
            key={c.id}
            className={`chip ${category === c.id ? "active" : ""}`}
            onClick={() => setCategory(c.id)}
          >
            <c.icon />
            {c.label}
          </button>
        ))}
      </div>
      <p className="muted small-text">
        {rows.length} places ·{" "}
        {venues[0]?.is_demo
          ? "Fictional inventory for demonstration"
          : "Published venue records"}
      </p>
      {rows.length ? (
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
        <Empty title="Nothing here yet">
          Try another category or search. Live venues appear after their
          essential facts have been verified.
        </Empty>
      )}
    </>
  );
}

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
    [busy, setBusy] = useState(true),
    [error, setError] = useState(""),
    [tab, setTab] = useState("plans");
  useEffect(() => {
    setBusy(true);
    api<Plan[]>("/plans")
      .then(setPlans)
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
      <div className="tabs">
        <button
          className={tab === "plans" ? "active" : ""}
          onClick={() => setTab("plans")}
        >
          Saved plans <span>{plans.length}</span>
        </button>
        <button
          className={tab === "places" ? "active" : ""}
          onClick={() => setTab("places")}
        >
          Saved places <span>{venues.filter((v) => v.saved).length}</span>
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
      ) : venues.some((v) => v.saved) ? (
        <div className="venue-grid">
          {venues
            .filter((v) => v.saved)
            .map((v) => (
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
      <div className="profile-grid">
        <form className="panel stack-form" onSubmit={save}>
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
              Learn from my confirmed visit feedback
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
              These modest signals come from food or activity scores on
              confirmed visits. A bookmark or skip never means you went.
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
          <section className="panel privacy-panel">
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
                    : "This clears preferences and confirmed visits. Saved places and plans stay."}
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
      <div className="section-heading">
        <h2>The places you’ve been.</h2>
        <span className="muted">Only visits you recorded</span>
      </div>
      {visits.length ? (
        <div className="visit-list">
          {visits.map((v) => (
            <article key={v.id}>
              <div>
                <strong>
                  {venues.find((p) => p.id === v.venue_id)?.name || "Venue"}
                </strong>
                <p>{v.note || "No note added"}</p>
              </div>
              <div>
                <strong>{v.rating}/5</strong>
                <small>
                  {v.visited_on} · {v.occasion}
                </small>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Your story starts with a visit">
          Open a place and choose “I visited” to tell us how it went.
        </Empty>
      )}
    </>
  );
}
