import { useEffect, useState, type FormEvent } from "react";
import { api, post } from "./api";
import { ErrorBox } from "./components";

type Report = {
  collection_coverage: {
    sources_found: number;
    classified_comments: number;
    active_spots: number;
    maps_reviewed: number;
    indexed_reference_images: number;
    missing_menu: number;
    missing_hours: number;
    missing_vibes: number;
    limitation: string;
  };
  labelled_tasks: number;
  heldout_tasks: number;
  status: string;
  blockers: string[];
  name_precision: number | null;
  name_recall: number | null;
  creator_calibration: {
    groups: number;
    brier_score: number | null;
    status: string;
  };
  sources: { id: string; url: string; roles: string[]; labels: string[] }[];
  comparisons: {
    source_id: string;
    results: Record<
      string,
      { baseline: unknown; with_corrections: unknown; scope: string }
    >;
  }[];
};
type Source = {
  id: string;
  url: string;
  comment_texts: string[];
  predictions: Record<
    string,
    {
      venue_candidates?: { name: string }[];
      transcript?: string;
      visual_text?: string;
    }
  >;
};
const kinds = [
  "firsthand_claim",
  "question",
  "promotion",
  "correction",
  "opinion",
  "unrelated",
  "unclear",
];

export default function Evaluation() {
  const [report, setReport] = useState<Report | null>(null),
    [source, setSource] = useState<Source | null>(null);
  const [sourceId, setSourceId] = useState(""),
    [role, setRole] = useState("caption"),
    [language, setLanguage] = useState("en");
  const [names, setNames] = useState(""),
    [transcript, setTranscript] = useState(""),
    [visualText, setVisualText] = useState("");
  const [evaluateNames, setEvaluateNames] = useState(true),
    [evaluateSpeech, setEvaluateSpeech] = useState(false),
    [evaluateText, setEvaluateText] = useState(false);
  const [labels, setLabels] = useState<Record<number, string>>({}),
    [checked, setChecked] = useState(false),
    [note, setNote] = useState("");
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const refresh = () =>
    api<Report>("/admin/evaluation")
      .then(setReport)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void refresh();
  }, []);
  useEffect(() => {
    setSource(null);
    setNames("");
    setTranscript("");
    setVisualText("");
    setLabels({});
    setChecked(false);
    setNote("");
    if (!sourceId) return;
    let current = true;
    api<Source>(`/admin/evaluation/sources/${sourceId}`)
      .then((s) => {
        if (current) setSource(s);
      })
      .catch((e) => setError(e.message));
    return () => {
      current = false;
    };
  }, [sourceId]);
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await post<{ split: string }>(
        `/admin/evaluation/sources/${sourceId}/label`,
        {
          role,
          language,
          evaluate_names: evaluateNames,
          expected_names: names
            .split("\n")
            .map((n) => n.trim())
            .filter(Boolean),
          transcript: role === "video" && evaluateSpeech ? transcript : null,
          visual_text: role === "video" && evaluateText ? visualText : null,
          comment_labels:
            role === "comments"
              ? Object.fromEntries(Object.entries(labels).filter(([, v]) => v))
              : {},
          source_checked: checked,
          note,
        },
      );
      setMessage(
        `Review saved in the ${result.split} evaluation group. No location was approved.`,
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Instagram accuracy review</h2>
      <p>
        Review examples the agent found. Check the original source before
        entering expected answers. A model prediction is not a reference answer.
      </p>
      <ErrorBox message={error} />
      {message && <p role="status">{message}</p>}
      {report && (
        <>
          <p>
            Collection: {report.collection_coverage.sources_found} source
            records, {report.collection_coverage.classified_comments} classified
            comments, {report.collection_coverage.indexed_reference_images}{" "}
            reference images.
          </p>
          <p>
            Inventory: {report.collection_coverage.active_spots} active drafts,{" "}
            {report.collection_coverage.maps_reviewed} Maps identities reviewed.
            Missing evidence: {report.collection_coverage.missing_menu} menus,{" "}
            {report.collection_coverage.missing_hours} opening hours,{" "}
            {report.collection_coverage.missing_vibes} atmosphere descriptions.
          </p>
          <p className="small-text">{report.collection_coverage.limitation}</p>
          <p>
            {report.labelled_tasks} labelled tasks · {report.heldout_tasks}{" "}
            held-out tasks. {report.status.replaceAll("_", " ")}
          </p>
          <p>
            Venue-name precision:{" "}
            {report.name_precision == null
              ? "Not measured"
              : `${Math.round(report.name_precision * 100)}%`}
            . Recall:{" "}
            {report.name_recall == null
              ? "Not measured"
              : `${Math.round(report.name_recall * 100)}%`}
            .
          </p>
          <details>
            <summary>Evaluation requirements</summary>
            <ul>
              {report.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
            <p>
              These are provisional engineering thresholds. Real user outcomes
              and representative sampling are still required.
            </p>
          </details>
          <p>
            Creator reliability: {report.creator_calibration.groups} prospective
            reviewed groups; calibration{" "}
            {report.creator_calibration.status.replaceAll("_", " ")}.
          </p>
          <form className="stack-form" onSubmit={save}>
            <label>
              Discovered source
              <select
                required
                value={sourceId}
                onChange={(e) => {
                  setSourceId(e.target.value);
                  setRole("caption");
                }}
              >
                <option value="">Choose a collected source</option>
                {report.sources
                  .filter((s) => s.roles.length)
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.url} · reviewed tasks: {s.labels.join(", ") || "none"}
                    </option>
                  ))}
              </select>
            </label>
            {source && (
              <>
                <a href={source.url} target="_blank" rel="noreferrer">
                  Inspect original reel/post
                </a>
                <label>
                  Task
                  <select
                    value={role}
                    onChange={(e) => {
                      setRole(e.target.value);
                      setChecked(false);
                      setNames("");
                      setLabels({});
                      setTranscript("");
                      setVisualText("");
                    }}
                  >
                    {["caption", "comments", "video"].map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Source language code
                  <input
                    required
                    minLength={2}
                    maxLength={30}
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    placeholder="en or ta"
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={evaluateNames}
                    onChange={(e) => setEvaluateNames(e.target.checked)}
                  />
                  Evaluate venue names
                </label>
                {evaluateNames && (
                  <label>
                    Correct venue names, one per line (leave empty if no venue
                    is named)
                    <textarea
                      value={names}
                      onChange={(e) => setNames(e.target.value)}
                    />
                  </label>
                )}
                {role === "video" && (
                  <>
                    <label>
                      <input
                        type="checkbox"
                        checked={evaluateSpeech}
                        onChange={(e) => setEvaluateSpeech(e.target.checked)}
                      />
                      Evaluate speech transcription
                    </label>
                    {evaluateSpeech && (
                      <label>
                        Exact original-language transcript for the analysed clip
                        (up to 2,000 characters)
                        <textarea
                          maxLength={2000}
                          value={transcript}
                          onChange={(e) => setTranscript(e.target.value)}
                        />
                      </label>
                    )}
                    <label>
                      <input
                        type="checkbox"
                        checked={evaluateText}
                        onChange={(e) => setEvaluateText(e.target.checked)}
                      />
                      Evaluate visible lettering
                    </label>
                    {evaluateText && (
                      <label>
                        Exact readable text at the analysed frame times (up to
                        2,000 characters)
                        <textarea
                          maxLength={2000}
                          value={visualText}
                          onChange={(e) => setVisualText(e.target.value)}
                        />
                      </label>
                    )}
                  </>
                )}
                {role === "comments" && (
                  <details open>
                    <summary>
                      Label collected comments ({source.comment_texts.length})
                    </summary>
                    {source.comment_texts.length === 0 && (
                      <p>
                        Original comment text is unavailable or expired. Do not
                        guess labels.
                      </p>
                    )}
                    {source.comment_texts.map((text, i) => (
                      <label key={i}>
                        Comment {i + 1}: {text}
                        <select
                          value={labels[i] || ""}
                          onChange={(e) =>
                            setLabels({ ...labels, [i]: e.target.value })
                          }
                        >
                          <option value="">Leave unlabelled</option>
                          {kinds.map((k) => (
                            <option key={k} value={k}>
                              {k.replaceAll("_", " ")}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </details>
                )}
                <details>
                  <summary>Current machine prediction (unverified)</summary>
                  <pre>{JSON.stringify(source.predictions[role], null, 2)}</pre>
                </details>
                <label>
                  Review notes
                  <textarea
                    required
                    minLength={10}
                    maxLength={1000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                  />
                </label>
                <label>
                  <input
                    type="checkbox"
                    required
                    checked={checked}
                    onChange={(e) => setChecked(e.target.checked)}
                  />
                  I inspected the original source and checked these reference
                  answers.
                </label>
                <button className="primary" disabled={busy}>
                  Save evaluation labels
                </button>
                {role !== "video" && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      setError("");
                      try {
                        await post(
                          `/admin/evaluation/sources/${sourceId}/compare`,
                          { role },
                        );
                        setMessage(
                          "Local correction comparison queued. Refresh after the worker finishes.",
                        );
                      } catch (e) {
                        setError((e as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Compare with independent corrections
                  </button>
                )}
                <button
                  type="button"
                  className="secondary"
                  disabled={busy}
                  onClick={async () => {
                    try {
                      await api(
                        `/admin/evaluation/sources/${sourceId}/labels`,
                        { method: "DELETE" },
                      );
                      setMessage("Evaluation labels revoked.");
                      await refresh();
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  Revoke labels for this source
                </button>
              </>
            )}
          </form>
          <button
            type="button"
            className="secondary"
            onClick={() => void refresh()}
          >
            Refresh evaluation
          </button>
          {!!report.comparisons.length && (
            <details>
              <summary>Correction comparison results</summary>
              <pre>{JSON.stringify(report.comparisons, null, 2)}</pre>
            </details>
          )}
        </>
      )}
    </section>
  );
}
