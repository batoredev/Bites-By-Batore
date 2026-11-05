import { useState } from "react";
import { post } from "./api";
import { ErrorBox } from "./components";
import type { OutingRequest } from "./types";

type Reply = {
  ready: boolean;
  key?: string;
  question?: string;
  answers: Record<string, string>;
  choices?: { value: string; label: string }[];
  suggestion?: Partial<OutingRequest>;
  message: string;
  memory_basis?: string;
};

export default function DiscoveryGuide({
  request,
  apply,
}: {
  request: OutingRequest;
  apply: (r: OutingRequest) => void;
}) {
  const [reply, setReply] = useState<Reply | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function answer(answers: Record<string, string>) {
    setBusy(true);
    setError("");
    try {
      setReply(
        await post<Reply>("/discovery/conversation", {
          message: request.query,
          answers,
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="discovery-guide">
      {!reply ? (
        <button
          className="text-button"
          type="button"
          disabled={busy}
          onClick={() => answer({})}
        >
          Not sure? Help me decide.
        </button>
      ) : (
        <>
          <p role="status">{reply.ready ? reply.message : reply.question}</p>
          <div className="mood-row">
            {reply.choices?.map((c) => (
              <button
                type="button"
                className="chip"
                key={c.value}
                disabled={busy}
                onClick={() =>
                  answer({ ...reply.answers, [reply.key!]: c.value })
                }
              >
                {c.label}
              </button>
            ))}
          </div>
          {reply.ready && (
            <>
              <p className="small-text muted">
                {reply.memory_basis} Your budget, location and available time
                stay as entered.
              </p>
              <button
                className="secondary"
                type="button"
                onClick={() => {
                  apply({ ...request, ...reply.suggestion });
                  setReply(null);
                }}
              >
                Use this direction
              </button>
            </>
          )}
          <button
            className="text-button"
            type="button"
            disabled={busy}
            onClick={() => setReply(null)}
          >
            Start over
          </button>
        </>
      )}
      <ErrorBox message={error} />
    </div>
  );
}
