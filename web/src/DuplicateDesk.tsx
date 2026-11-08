import { useEffect, useState, type FormEvent } from "react";
import { api, post, dateText } from "./api";
import { ErrorBox, Loading, Modal } from "./components";

interface DuplicateSpot {
  id: string;
  name: string;
  area: string;
  status: string;
  venue_id?: string | null;
}

interface DuplicateCandidate {
  key: string;
  left: DuplicateSpot;
  right: DuplicateSpot;
  decision: "review";
  reasons: string[];
  conflicts: string[];
}

interface DuplicateReport {
  agent: {
    state: string;
    last_completed_at: string | null;
    job_id: string | null;
  };
  candidates: DuplicateCandidate[];
  pending_count: number;
}

const inactive = ["merged", "quarantined", "rejected", "prepared"];
const canSurvive = (spot: DuplicateSpot) =>
  !spot.venue_id && !inactive.includes(spot.status);
const canMergeSource = (spot: DuplicateSpot) =>
  !spot.venue_id && !["merged", "rejected", "prepared"].includes(spot.status);
const survivors = (candidate: DuplicateCandidate) =>
  [candidate.left, candidate.right].filter(
    (spot) =>
      canSurvive(spot) &&
      canMergeSource(
        spot.id === candidate.left.id ? candidate.right : candidate.left,
      ),
  );

function PairEvidence({ candidate }: { candidate: DuplicateCandidate }) {
  return (
    <>
      {[candidate.left, candidate.right].map((spot) => (
        <p key={spot.id}>
          <strong>{spot.name}</strong> — {spot.area || "Area unconfirmed"} ·{" "}
          {spot.status.replaceAll("_", " ")}
          {spot.venue_id ? " · prepared venue" : ""}
          <br />
          <small>Record {spot.id}</small>
        </p>
      ))}
      <p>Why this pair needs review:</p>
      <ul>
        {candidate.reasons.map((reason, i) => (
          <li key={i}>{reason}</li>
        ))}
      </ul>
      {!!candidate.conflicts.length && (
        <>
          <p>Unresolved branch conflicts:</p>
          <ul>
            {candidate.conflicts.map((conflict, i) => (
              <li key={i}>{conflict}</li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

function ReviewPair({
  candidate,
  close,
  saved,
}: {
  candidate: DuplicateCandidate;
  close: () => void;
  saved: () => void;
}) {
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const choices = survivors(candidate);
  const target = choices.find((spot) => spot.id === targetId);
  const source = target
    ? target.id === candidate.left.id
      ? candidate.right
      : candidate.left
    : null;
  const valid = !!target && !!source && checked && reason.trim().length >= 10;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!valid || busy || !source) return;
    setBusy(true);
    setError("");
    try {
      await post(`/admin/spots/${encodeURIComponent(source.id)}/merge`, {
        target_id: targetId,
        same_branch_checked: true,
        reason: reason.trim(),
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
    <Modal title="Review duplicate branch" onClose={close}>
      <form className="stack-form" onSubmit={submit}>
        <PairEvidence candidate={candidate} />
        <p>
          Check the original evidence and exact address before merging.
          Different or unresolved branches must stay separate. This review does
          not approve a Maps identity, location or fact.
        </p>
        <ErrorBox message={error} />
        <label>
          Surviving draft
          <select
            required
            disabled={busy}
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
          >
            <option value="">Choose the record to keep active</option>
            {choices.map((spot) => (
              <option key={spot.id} value={spot.id}>
                {spot.name} — {spot.area || "area unconfirmed"} ({spot.id})
              </option>
            ))}
          </select>
        </label>
        {source && (
          <p>
            Merge {source.name} ({source.id}) into {target?.name}. The original
            record and source evidence are retained.
          </p>
        )}
        <label>
          Evidence for this exact same branch
          <textarea
            required
            minLength={10}
            maxLength={1000}
            disabled={busy}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <label className="check-row">
          <input
            type="checkbox"
            required
            disabled={busy}
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
          />
          I checked that both records refer to the exact same branch.
        </label>
        <button className="primary" disabled={busy || !valid}>
          Merge checked duplicate and retain evidence
        </button>
      </form>
    </Modal>
  );
}

export default function DuplicateDesk({
  onChanged,
}: {
  onChanged: () => void;
}) {
  const [report, setReport] = useState<DuplicateReport | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<DuplicateCandidate | null>(null);

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setReport(await api<DuplicateReport>("/admin/spots/duplicates"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function run() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await post<{ job_id: string; state: string }>(
        "/admin/spots/duplicates/run",
      );
      setReport((current) =>
        current
          ? {
              ...current,
              agent: {
                ...current.agent,
                state: result.state,
                job_id: result.job_id,
              },
            }
          : current,
      );
      setMessage("Duplicate scan queued. Refresh to read its saved results.");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const query = filter.trim().toLocaleLowerCase();
  const filtered = (report?.candidates || []).filter((candidate) =>
    [
      candidate.left.name,
      candidate.left.area,
      candidate.right.name,
      candidate.right.area,
      ...candidate.reasons,
      ...candidate.conflicts,
    ]
      .join(" ")
      .toLocaleLowerCase()
      .includes(query),
  );
  const lastPage = Math.max(0, Math.ceil(filtered.length / 20) - 1);
  const currentPage = Math.min(page, lastPage);
  const start = currentPage * 20;
  const scanning = ["queued", "running"].includes(report?.agent.state || "");

  return (
    <section className="panel" aria-label="Duplicate review desk">
      <h3>Duplicate review desk</h3>
      <p>
        The duplicate agent checks saved drafts for repeated locations. Similar
        names and conflicting branches need your review. Merging keeps original
        evidence; location and fact approvals remain separate.
      </p>
      {report && (
        <div role="status" aria-label="Duplicate agent status">
          <p>
            Duplicate agent: {report.agent.state.replaceAll("_", " ")} ·{" "}
            {report.pending_count} pairs awaiting review
          </p>
          <p className="small-text">
            {report.agent.last_completed_at
              ? `Last completed scan: ${dateText(report.agent.last_completed_at)}`
              : "No completed duplicate scan recorded."}
            {report.agent.job_id ? ` · Job ${report.agent.job_id}` : ""}
          </p>
        </div>
      )}
      <div className="inline-actions">
        <button
          className="secondary"
          disabled={busy}
          onClick={() => void refresh()}
        >
          Refresh duplicate review
        </button>
        <button
          className="secondary"
          disabled={busy || scanning}
          onClick={() => void run()}
        >
          Run duplicate agent
        </button>
      </div>
      <ErrorBox message={error} />
      {message && <p role="status">{message}</p>}
      {!report && busy && <Loading label="Reading duplicate review…" />}
      {report && (
        <>
          {!!report.candidates.length && (
            <label>
              Filter duplicate pairs
              <input
                type="search"
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value);
                  setPage(0);
                }}
              />
            </label>
          )}
          {filtered.length ? (
            <>
              <p>
                Showing {start + 1}–{Math.min(start + 20, filtered.length)} of{" "}
                {filtered.length} review pairs
                {query ? " matching this filter" : ""}.
              </p>
              <div className="review-grid">
                {filtered.slice(start, start + 20).map((candidate) => (
                  <article className="review-card" key={candidate.key}>
                    <h4>
                      {candidate.left.name} / {candidate.right.name}
                    </h4>
                    <PairEvidence candidate={candidate} />
                    {survivors(candidate).length ? (
                      <button
                        className="secondary"
                        onClick={() => setSelected(candidate)}
                      >
                        Review this duplicate pair
                      </button>
                    ) : (
                      <p>
                        This pair needs an active, unprepared survivor before
                        merging.
                      </p>
                    )}
                  </article>
                ))}
              </div>
              {filtered.length > 20 && (
                <div
                  className="inline-actions"
                  role="group"
                  aria-label="Duplicate review pages"
                >
                  <button
                    className="secondary"
                    disabled={currentPage === 0}
                    onClick={() => setPage(currentPage - 1)}
                  >
                    Previous duplicate pairs
                  </button>
                  <button
                    className="secondary"
                    disabled={currentPage === lastPage}
                    onClick={() => setPage(currentPage + 1)}
                  >
                    Next duplicate pairs
                  </button>
                </div>
              )}
            </>
          ) : (
            <p>
              {query
                ? "No duplicate pairs match this filter."
                : "No duplicate pairs are currently awaiting review. This does not confirm all branch identities."}
            </p>
          )}
        </>
      )}
      {selected && (
        <ReviewPair
          key={selected.key}
          candidate={selected}
          close={() => setSelected(null)}
          saved={() => {
            setMessage(
              "Duplicate merged. Original records and evidence retained; approvals are unchanged.",
            );
            void refresh();
            onChanged();
          }}
        />
      )}
    </section>
  );
}
