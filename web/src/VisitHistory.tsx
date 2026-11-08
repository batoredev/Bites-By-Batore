import { useState, type FormEvent } from "react";
import { api } from "./api";
import { ErrorBox } from "./components";
import { today } from "./DishDiary";
import type { Visit } from "./types";

export default function VisitHistory({
  visit,
  venueName,
  changed,
}: {
  visit: Visit;
  venueName: string;
  changed: () => void;
}) {
  const [editing, setEditing] = useState(false),
    [rating, setRating] = useState(visit.rating),
    [note, setNote] = useState(visit.note),
    [date, setDate] = useState(visit.visited_on),
    [occasion, setOccasion] = useState(visit.occasion);
  const [dimensions, setDimensions] = useState(visit.dimensions),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function save(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api(`/visits/${visit.id}`, {
        method: "PUT",
        body: JSON.stringify({
          venue_id: visit.venue_id,
          rating,
          note,
          visited_on: date,
          occasion,
          dimensions,
        }),
      });
      setEditing(false);
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    setError("");
    setBusy(true);
    try {
      await api(`/visits/${visit.id}`, { method: "DELETE" });
      changed();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article className="visit-history-item">
      <div>
        <strong>{venueName}</strong>
        <p>{visit.note || "No note added"}</p>
        <small>
          {visit.visited_on} · {visit.occasion} · {visit.rating}/5
        </small>
        <div className="inline-actions">
          <button
            className="text-button"
            type="button"
            disabled={busy}
            onClick={() => {
              setRating(visit.rating);
              setNote(visit.note);
              setDate(visit.visited_on);
              setOccasion(visit.occasion);
              setDimensions(visit.dimensions);
              setEditing(true);
            }}
          >
            Edit visit
          </button>
          <button
            className="text-button danger"
            type="button"
            disabled={busy}
            onClick={remove}
          >
            Delete visit
          </button>
        </div>
        {editing && (
          <form onSubmit={save} className="stack-form">
            <label>
              Visit date
              <input
                type="date"
                required
                max={today()}
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <label>
              Overall experience
              <select
                value={rating}
                onChange={(e) => setRating(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>
                    {n}/5
                  </option>
                ))}
              </select>
            </label>
            {Object.entries(dimensions).map(([key, value]) => (
              <label key={key}>
                {key[0].toUpperCase() + key.slice(1)} score
                <select
                  value={value}
                  onChange={(e) =>
                    setDimensions({
                      ...dimensions,
                      [key]: Number(e.target.value),
                    })
                  }
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}/5
                    </option>
                  ))}
                </select>
              </label>
            ))}
            <label>
              Occasion
              <input
                maxLength={60}
                value={occasion}
                onChange={(e) => setOccasion(e.target.value)}
              />
            </label>
            <label>
              Your visit note
              <textarea
                maxLength={1000}
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
            <div className="inline-actions">
              <button className="primary" disabled={busy}>
                Update visit
              </button>
              <button
                className="text-button"
                type="button"
                onClick={() => setEditing(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
        <ErrorBox message={error} />
      </div>
    </article>
  );
}
