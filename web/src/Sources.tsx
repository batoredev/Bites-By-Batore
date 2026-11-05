import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowRight,
  FilmStrip,
  Link,
  ArrowsClockwise,
  Trash,
  Translate,
} from "@phosphor-icons/react";
import { api, post, dateText, safeLink } from "./api";
import { PageTitle, ErrorBox, Empty } from "./components";
import type { Config, Submission } from "./types";
import Research from "./Research";

function Observation({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "")
    return <span className="muted">Not supplied</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ul className="observations">
        {value.map((v, i) => (
          <li key={i}>
            <Observation value={v} />
          </li>
        ))}
      </ul>
    ) : (
      <span className="muted">None established</span>
    );
  if (typeof value === "object")
    return (
      <div className="analysis-fields">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <strong>{k.replaceAll("_", " ")}</strong>
            <Observation value={v} />
          </div>
        ))}
      </div>
    );
  return (
    <span>
      {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
    </span>
  );
}
export default function Sources({ config }: { config: Config }) {
  const [url, setUrl] = useState(""),
    [caption, setCaption] = useState(""),
    [comments, setComments] = useState(""),
    [transcript, setTranscript] = useState(""),
    [creator, setCreator] = useState(""),
    [file, setFile] = useState<File | null>(null),
    [items, setItems] = useState<Submission[]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [open, setOpen] = useState("");
  const load = () =>
    api<Submission[]>("/submissions")
      .then(setItems)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
    const timer = setInterval(load, 15000);
    return () => clearInterval(timer);
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const item = await post<Submission>("/submissions", {
        url,
        caption: caption || (file ? "User supplied video for analysis." : ""),
        comments,
        transcript,
        creator,
      });
      if (file) {
        const form = new FormData();
        form.set("file", file);
        await api(`/submissions/${item.id}/media`, {
          method: "POST",
          body: form,
        });
      }
      setMessage(
        "Added to your analysis queue. The worker will process it in the background.",
      );
      setOpen(item.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove(id: string) {
    try {
      await api(`/submissions/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="FROM YOUR FEED TO A REAL POSSIBILITY"
        title="Found something worth a look?"
        description="Bring a reel, a video or a creator’s recommendation. We’ll keep the evidence and the unknowns together."
      />
      <div className="source-layout">
        <form className="panel stack-form" onSubmit={submit}>
          <div className="form-intro">
            <h2>Share a find</h2>
            <FilmStrip size={25} />
          </div>
          <label>
            Instagram or YouTube link
            <input
              type="url"
              value={url}
              maxLength={2000}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.instagram.com/reel/…"
            />
          </label>
          <label>
            Caption or description
            <textarea
              value={caption}
              maxLength={10000}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Paste the description, address clues or dishes mentioned…"
            />
          </label>
          <div className="two-col">
            <label>
              Creator name <small>Optional</small>
              <input
                value={creator}
                maxLength={100}
                onChange={(e) => setCreator(e.target.value)}
              />
            </label>
            <label>
              Video file <small>Up to {config.max_media_mb} MB</small>
              <input
                type="file"
                accept="video/mp4,video/webm,video/quicktime"
                onChange={(e) => {
                  const next = e.target.files?.[0];
                  if (next && next.size > config.max_media_mb * 1024 * 1024) {
                    setError(`Choose a file under ${config.max_media_mb} MB.`);
                    e.target.value = "";
                  } else setFile(next || null);
                }}
              />
            </label>
          </div>
          <details className="source-extra">
            <summary>Add comments or a transcript</summary>
            <label>
              Comments you can share
              <textarea
                value={comments}
                maxLength={15000}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Keep each comment on a separate line. Remove personal contact details."
              />
            </label>
            <label>
              Transcript
              <textarea
                value={transcript}
                maxLength={20000}
                onChange={(e) => setTranscript(e.target.value)}
              />
            </label>
          </details>
          <p className="small-text muted">
            Share only material you can provide for analysis. Uploaded video
            bytes are removed after processing or after one day.
          </p>
          <button
            className="primary"
            disabled={
              busy || !(url || caption || transcript || comments || file)
            }
          >
            {busy ? "Adding your find…" : "Add to analysis"}
            <ArrowRight />
          </button>
          <ErrorBox message={error} />
          {message && (
            <div className="success" role="status">
              {message}
            </div>
          )}
        </form>
        <aside>
          <div className="source-note">
            <Translate size={30} />
            <h2>
              Any language.
              <br />
              Clearer understanding.
            </h2>
            <p>
              Supplied video, speech and text can be analyzed across languages.
              Results are presented in English, with translation uncertainty
              kept visible.
            </p>
            <ol>
              <li>Read the caption and available comments.</li>
              <li>Inspect video clues and spoken details.</li>
              <li>Separate observations from guesses.</li>
              <li>Verify the exact place and current facts.</li>
            </ol>
            <p className="small-text">
              Likes show attention. They do not prove that a recommendation is
              accurate.
            </p>
          </div>
          <div className="notice">
            {config.mode === "demo"
              ? "Demo mode saves your material and demonstrates processing states. It does not run live AI analysis."
              : "Instagram links may need supplied media or text. A link alone does not provide access to every reel or comment."}
          </div>
        </aside>
      </div>
      <Research />
      <div className="section-heading">
        <div>
          <div className="eyebrow">YOUR RESEARCH SHELF</div>
          <h2>Finds worth following up.</h2>
        </div>
        <button className="secondary" onClick={load}>
          <ArrowsClockwise />
          Refresh
        </button>
      </div>
      {items.length ? (
        <div className="submission-list">
          {items.map((item) => (
            <article className="panel" key={item.id}>
              <div className="submission-head">
                <button
                  className="text-button"
                  onClick={() => setOpen(open === item.id ? "" : item.id)}
                >
                  <Link size={20} />
                  <strong>
                    {item.url
                      ? new URL(item.url).hostname
                      : "Shared text & media"}
                  </strong>
                  <span className={`status ${item.status}`}>
                    {item.status.replaceAll("_", " ")}
                  </span>
                </button>
                <button
                  className="icon-button"
                  aria-label="Delete submission"
                  onClick={() => remove(item.id)}
                >
                  <Trash />
                </button>
              </div>
              <small className="muted">{dateText(item.created_at)}</small>
              {safeLink(item.url) && (
                <a
                  className="source-link"
                  href={safeLink(item.url)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open original source
                </a>
              )}
              {open === item.id && (
                <div className="analysis-result">
                  <button
                    type="button"
                    className="secondary"
                    onClick={async () => {
                      try {
                        await post("/investigations", {
                          query: "Investigate this food or entertainment find",
                          submission_id: item.id,
                        });
                        setMessage(
                          "Investigation started. Its specialist progress will appear above.",
                        );
                      } catch (err) {
                        setError((err as Error).message);
                      }
                    }}
                  >
                    Investigate this find
                  </button>
                  {Object.keys(item.result).length ? (
                    <Observation value={item.result} />
                  ) : (
                    <p className="muted">
                      Waiting for the background worker. This page checks for
                      updates every 15 seconds.
                    </p>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Your first find belongs here">
          Share a video or caption to start building an evidence trail.
        </Empty>
      )}
    </>
  );
}
