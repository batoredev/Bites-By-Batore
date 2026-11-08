import { useEffect, useState, type FormEvent } from "react";
import { api, money, safeLink, dateText } from "./api";
import { Empty, ErrorBox } from "./components";
import type { Venue, DishEntry, DishStatus, MenuItem, MenuView } from "./types";

const labels: Record<DishStatus, string> = {
  want_to_try: "Want to try",
  tried: "Tried",
  favourite: "Favourite",
  not_for_me: "Not for me",
};
export const today = () =>
  new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

function ExperienceFields({
  status,
  setStatus,
  date,
  setDate,
  note,
  setNote,
}: {
  status: DishStatus;
  setStatus: (s: DishStatus) => void;
  date: string;
  setDate: (s: string) => void;
  note: string;
  setNote: (s: string) => void;
}) {
  return (
    <>
      <div className="two-col">
        <label>
          Your experience
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as DishStatus)}
          >
            {Object.entries(labels).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {status !== "want_to_try" && (
          <label>
            Date you tried it
            <input
              type="date"
              required
              max={today()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
        )}
      </div>
      <label>
        Your private note
        <textarea
          maxLength={1000}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </label>
    </>
  );
}

export function MenuPanel({
  venue,
  changed,
}: {
  venue: Venue;
  changed: () => void;
}) {
  const [menu, setMenu] = useState<MenuView | undefined>(venue.menu);
  const [selected, setSelected] = useState<MenuItem | null>(null);
  const [status, setStatus] = useState<DishStatus>("tried"),
    [date, setDate] = useState(today()),
    [note, setNote] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  useEffect(() => setMenu(venue.menu), [venue.menu]);
  async function save(item: MenuItem, next: DishStatus) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(`/venues/${venue.id}/dish-diary/${item.key}`, {
        method: "PUT",
        body: JSON.stringify({
          status: next,
          note: next === "want_to_try" ? "" : note,
          tried_on: next === "want_to_try" ? null : date,
        }),
      });
      const updated = await api<Venue>(`/venues/${venue.id}`);
      setMenu(updated.menu);
      setSelected(null);
      setNote("");
      setMessage(
        next === "want_to_try"
          ? "Saved to your private dish diary. This does not record a visit."
          : "Dish experience saved. You can edit or remove it in My taste.",
      );
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!menu || menu.status !== "current")
    return (
      <section className="menu-panel">
        <h3>Menu and dish suggestions</h3>
        <p>
          {menu?.status === "expired"
            ? "The reviewed menu has expired. Current dish and price suggestions are unavailable until it is checked again."
            : "A reviewed menu is not available yet. Dish names and prices will appear after evidence review."}
        </p>
      </section>
    );
  return (
    <section className="menu-panel">
      <h3>Menu and dish suggestions</h3>
      <p className="small-text muted">
        {menu.basis}. {menu.price_note}.
      </p>
      {menu.dining_format && (
        <p>
          Dining format:{" "}
          <strong>{menu.dining_format.replaceAll("_", " ")}</strong>
        </p>
      )}
      <div className="menu-list">
        {menu.items.map((item) => (
          <article className="menu-item" key={item.key}>
            <div className="section-heading">
              <h4>{item.name}</h4>
              <strong>
                {item.price_inr === null
                  ? "Price unknown"
                  : `${money(item.price_inr)} / ${item.unit}`}
              </strong>
            </div>
            <p className="small-text muted">
              {[
                item.cuisine,
                item.vegetarian === true
                  ? "Vegetarian recorded"
                  : item.vegetarian === false
                    ? "Non-vegetarian recorded"
                    : "Vegetarian status unknown",
                item.spice ? `${item.spice} spice` : "Spice level unknown",
                item.available === false
                  ? "Recorded unavailable"
                  : item.available === true
                    ? "Recorded available"
                    : "Current availability unconfirmed",
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {item.eligible_pick ? (
              item.reasons.map((reason) => (
                <p key={reason} className="small-text">
                  {reason}
                </p>
              ))
            ) : (
              <p className="small-text">
                Excluded from your picks because of your preferences or recorded
                availability.
              </p>
            )}
            {!!item.review_support?.groups && (
              <details className="review-sources">
                <summary>
                  Reviewed review evidence ({item.review_support.groups} groups)
                </summary>
                <p className="small-text muted">{item.review_support.basis}</p>
                <ul>
                  {item.review_support.sources.map((group, i) => (
                    <li key={i}>
                      <strong>{group.sentiment}</strong>
                      {group.sources.map((source) => (
                        <p className="small-text" key={source.url}>
                          {safeLink(source.url) && (
                            <a
                              href={safeLink(source.url)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Source evidence
                            </a>
                          )}{" "}
                          · observed {dateText(source.observed_at)} · check by{" "}
                          {dateText(source.expires_at)}
                        </p>
                      ))}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <p className="small-text muted">
              Observed {dateText(item.observed_at)} · check by{" "}
              {dateText(item.expires_at)}{" "}
              {safeLink(item.source_url) ? (
                <a
                  href={safeLink(item.source_url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Menu source
                </a>
              ) : venue.is_demo ? (
                "· Fictional demonstration menu"
              ) : (
                ""
              )}
            </p>
            {item.diary_status && (
              <p className="tiny-tag">
                Your diary: {labels[item.diary_status]}
              </p>
            )}
            <div className="inline-actions">
              <button
                className="secondary"
                type="button"
                disabled={busy || !!item.diary_status}
                onClick={() => save(item, "want_to_try")}
              >
                Save {item.name} to try
              </button>
              <button
                className="text-button"
                type="button"
                disabled={busy}
                onClick={() => {
                  setSelected(item);
                  setStatus("tried");
                  setNote("");
                }}
              >
                Record dish experience
              </button>
            </div>
          </article>
        ))}
      </div>
      {!menu.items.length && <p>No dishes are listed in this reviewed menu.</p>}
      {selected && (
        <form
          className="stack-form panel"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            void save(selected, status);
          }}
        >
          <h4>Record {selected.name}</h4>
          <ExperienceFields
            status={status}
            setStatus={setStatus}
            date={date}
            setDate={setDate}
            note={note}
            setNote={setNote}
          />
          <div className="inline-actions">
            <button className="primary" disabled={busy}>
              Save dish experience
            </button>
            <button
              className="text-button"
              type="button"
              onClick={() => setSelected(null)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      <ErrorBox message={error} />
      {message && (
        <p className="success" role="status">
          {message}
        </p>
      )}
    </section>
  );
}

export default function DishDiary({ changed }: { changed: () => void }) {
  const [entries, setEntries] = useState<DishEntry[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<DishEntry | null>(null),
    [filter, setFilter] = useState("all");
  const [status, setStatus] = useState<DishStatus>("tried"),
    [date, setDate] = useState(today()),
    [note, setNote] = useState("");
  const load = () =>
    api<DishEntry[]>("/dish-diary")
      .then(setEntries)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void load();
  }, []);
  async function remove(entry: DishEntry) {
    setBusy(true);
    setError("");
    try {
      await api(`/dish-diary/${entry.id}`, { method: "DELETE" });
      await load();
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setBusy(true);
    setError("");
    try {
      await api(
        `/venues/${editing.venue_id}/dish-diary/${editing.offering_key}`,
        {
          method: "PUT",
          body: JSON.stringify({
            status,
            note,
            tried_on: status === "want_to_try" ? null : date,
          }),
        },
      );
      setEditing(null);
      await load();
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const shown = entries.filter((e) => filter === "all" || e.status === filter);
  return (
    <section className="dish-diary" id="dish-diary">
      <div className="section-heading">
        <h2>Your private dish diary</h2>
        <span className="muted">
          Saved dishes are separate from venue visits
        </span>
      </div>
      <label>
        Filter your dishes
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All dishes</option>
          {Object.entries(labels).map(([k, v]) => (
            <option value={k} key={k}>
              {v}
            </option>
          ))}
        </select>
      </label>
      {shown.length ? (
        <div className="visit-list">
          {shown.map((entry) => (
            <article key={entry.id}>
              <div>
                <strong>{entry.name}</strong>
                <p>
                  {entry.venue_name} · {labels[entry.status]}
                  {entry.tried_on ? ` · ${entry.tried_on}` : ""}
                </p>
                {entry.note && <p>{entry.note}</p>}
              </div>
              <div className="inline-actions">
                <button
                  type="button"
                  className="text-button"
                  disabled={busy}
                  onClick={() => {
                    setEditing(entry);
                    setStatus(entry.status);
                    setDate(entry.tried_on || today());
                    setNote(entry.note);
                  }}
                >
                  Edit dish
                </button>
                <button
                  type="button"
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => remove(entry)}
                >
                  Remove dish
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="No dishes in this collection">
          Open a place with a reviewed menu to save a dish or record what you
          tried.
        </Empty>
      )}
      {editing && (
        <form className="panel stack-form" onSubmit={save}>
          <h3>Edit {editing.name}</h3>
          <ExperienceFields
            status={status}
            setStatus={setStatus}
            date={date}
            setDate={setDate}
            note={note}
            setNote={setNote}
          />
          <div className="inline-actions">
            <button className="primary" disabled={busy}>
              Update dish experience
            </button>
            <button
              type="button"
              className="text-button"
              onClick={() => setEditing(null)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      <ErrorBox message={error} />
    </section>
  );
}
