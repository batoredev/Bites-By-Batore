import { useEffect, useState, type FormEvent } from "react";
import { api, post } from "./api";
import { ErrorBox } from "./components";

type QualityReport = {
  categories: Record<string, { records: number; eligible: number }>;
  uncovered_categories: string[];
  launch_blockers: string[];
  delayed_jobs: number;
  budget_reserved_inr: number;
  monthly_budget_inr: number;
  budget_note: string;
  release_stage: string;
  venues: {
    venue_id: string;
    name: string;
    status: string;
    missing_critical: string[];
  }[];
};

export default function Quality() {
  const [data, setData] = useState<QualityReport | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const [reason, setReason] = useState(""),
    [busy, setBusy] = useState(false);
  const [checks, setChecks] = useState({
    coverage_checked: false,
    provider_smoke_tests_passed: false,
    backup_restore_passed: false,
    labelled_evaluation_passed: false,
  });
  const load = () =>
    api<QualityReport>("/admin/quality")
      .then(setData)
      .catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);
  async function review(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post("/admin/launch-review", { ...checks, approve: true, reason });
      setMessage(
        "Data review recorded. Invited access still requires release-stage configuration.",
      );
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h2>Coimbatore readiness</h2>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          try {
            const result = await post<{ message: string }>(
              "/admin/launch-leads",
            );
            setMessage(result.message);
          } catch (err) {
            setError((err as Error).message);
          }
        }}
      >
        Import researched Coimbatore leads
      </button>
      {message && <p role="status">{message}</p>}
      <ErrorBox message={error} />
      {data && (
        <>
          <p>
            Release stage: <strong>{data.release_stage}</strong>. Data
            verification comes before invited users.
          </p>
          <div className="notice">
            Reserved provider allowance: ₹{data.budget_reserved_inr} / ₹
            {data.monthly_budget_inr} this month.<p>{data.budget_note}</p>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Records</th>
                  <th>Eligible</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.categories).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{v.records}</td>
                    <td>{v.eligible}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            Uncovered categories:{" "}
            {data.uncovered_categories.join(", ") ||
              "None in the configured category list"}
            . These counts do not prove complete city coverage.
          </p>
          <p>Overdue queued jobs: {data.delayed_jobs}</p>
          <h3>Before inviting users</h3>
          <ul>
            {data.launch_blockers.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
          <details>
            <summary>Inspect missing essential facts</summary>
            <ul>
              {data.venues
                .filter((v) => v.missing_critical.length)
                .map((v) => (
                  <li key={v.venue_id}>
                    <strong>{v.name}</strong>: {v.missing_critical.join(", ")}
                  </li>
                ))}
            </ul>
          </details>
          <form className="panel stack-form" onSubmit={review}>
            <h3>Record the release data review</h3>
            {Object.keys(checks).map((key) => (
              <label className="check-label" key={key}>
                <input
                  type="checkbox"
                  checked={checks[key as keyof typeof checks]}
                  onChange={(e) =>
                    setChecks({ ...checks, [key]: e.target.checked })
                  }
                />
                {
                  {
                    coverage_checked: "Launch coverage independently checked",
                    provider_smoke_tests_passed:
                      "Actual provider smoke checks passed",
                    backup_restore_passed: "Staging backup and restore passed",
                    labelled_evaluation_passed:
                      "Human-labelled evidence evaluation passed",
                  }[key]
                }
              </label>
            ))}
            <label>
              Evidence and review notes
              <textarea
                minLength={30}
                required
                maxLength={2000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </label>
            <button
              className="primary"
              disabled={
                busy ||
                data.launch_blockers.length > 0 ||
                !Object.values(checks).every(Boolean)
              }
            >
              Record completed data review
            </button>
            {message && <p role="status">{message}</p>}
          </form>
        </>
      )}
    </section>
  );
}
