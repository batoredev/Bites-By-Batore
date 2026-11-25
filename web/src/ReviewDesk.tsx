import { useCallback, useEffect, useRef, useState } from "react";
import { api, post, safeLink } from "./api";
import { ErrorBox, Loading } from "./components";
import { parseCommand, type Command } from "./voiceCommands";

interface Match {
  name: string;
  area: string;
  category: string;
  status: string;
  coords: [number, number] | null;
  address: string;
  sources: string[];
  corroboration: string;
  websites: string[];
  search: string[];
  notes: string[];
  taught: boolean;
}

interface DeskItem {
  sheet: "decisions" | "overture";
  row: number;
  title: string;
  question: string;
  claim: string;
  answer: string;
  options: string[];
  maps_link: string;
  embed: string;
  matches: Match[];
  hints: string[];
}

interface Line {
  who: "you" | "desk";
  text: string;
}

type Recognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult:
    | ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }>; resultIndex: number }) => void)
    | null;
  onend: (() => void) | null;
  onerror: ((e: { error: string }) => void) | null;
};

type SpeechWindow = { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
const Recognizer =
  typeof window === "undefined"
    ? undefined
    : (window as unknown as SpeechWindow).SpeechRecognition ?? (window as unknown as SpeechWindow).webkitSpeechRecognition;
const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

const ANSWER_LABEL: Record<string, string> = { yes: "Yes", no: "No", closed: "Closed" };
const KEYS: Record<string, string> = { yes: "A", no: "X", closed: "C" };

function sourcesLine(item: DeskItem) {
  const m = item.matches[0];
  if (!m) return "I have nothing stored under this exact name, so check the map.";
  return [
    m.sources.length ? `Sources: ${m.sources.join(", ")}.` : "No named sources.",
    m.corroboration ? `Corroboration: ${m.corroboration.replace(/_/g, " ")}.` : "",
    m.websites.length ? `Website: ${m.websites[0]}.` : "",
    m.notes.length ? `Note: ${m.notes[0]}.` : "",
  ]
    .filter(Boolean)
    .join(" ");
}

function whereLine(item: DeskItem) {
  const m = item.matches[0];
  if (!m) return "I don't have a stored location; the map is searching by name.";
  return [
    m.area && `In ${m.area}.`,
    m.address && `Address: ${m.address}.`,
    m.coords ? "The pin is from stored coordinates." : "No coordinates yet.",
  ]
    .filter(Boolean)
    .join(" ");
}

const nextOpen = (from: number, list: DeskItem[]) => {
  for (let k = 1; k <= list.length; k++) {
    const j = (from + k) % list.length;
    if (!list[j].answer) return j;
  }
  return -1;
};

export default function ReviewDesk() {
  const [items, setItems] = useState<DeskItem[] | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [voice, setVoice] = useState(false);
  const [heard, setHeard] = useState("");
  const [log, setLog] = useState<Line[]>([]);
  const [history, setHistory] = useState<{ index: number; previous: string }[]>([]);
  const recognition = useRef<Recognition | null>(null);
  const speaking = useRef(false);
  const voiceOn = useRef(false);
  const handle = useRef<(c: Command, said: string) => void>(() => {});

  const item = items?.[index];
  const done = items?.filter((i) => i.answer).length ?? 0;
  const note = (who: Line["who"], text: string) => setLog((l) => [...l.slice(-30), { who, text }]);

  useEffect(() => {
    api<{ items: DeskItem[] }>("/admin/review-desk/items")
      .then((r) => {
        setItems(r.items);
        const first = r.items.findIndex((i) => !i.answer);
        setIndex(first < 0 ? 0 : first);
      })
      .catch((e) => setError(e.message));
  }, []);

  const say = useCallback((text: string) => {
    note("desk", text);
    if (!canSpeak || !voiceOn.current) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-IN";
    u.rate = 1.05;
    const indian = window.speechSynthesis.getVoices().find((v) => v.lang === "en-IN");
    if (indian) u.voice = indian;
    // Stop listening while talking so the desk never hears itself.
    speaking.current = true;
    recognition.current?.stop();
    u.onend = u.onerror = () => {
      speaking.current = false;
      if (voiceOn.current) {
        try {
          recognition.current?.start();
        } catch {
          /* already listening */
        }
      }
    };
    window.speechSynthesis.speak(u);
  }, []);

  const brief = (i: DeskItem, n: number, total: number) =>
    `Row ${n + 1} of ${total}. ${i.title}. ${i.claim} ${i.question}` + (i.answer ? ` You already said ${i.answer}.` : "");

  // Read each row aloud when it comes up, while voice is on.
  useEffect(() => {
    if (voice && item && items) say(brief(item, index, items.length));
  }, [voice, index, items?.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const answer = async (value: string) => {
    if (!items || !item || busy) return;
    if (!item.options.includes(value)) {
      say(`${ANSWER_LABEL[value]} doesn't fit this row. Say ${item.options.join(" or ")}.`);
      return;
    }
    setBusy(true);
    setError("");
    try {
      await post("/admin/review-desk/answer", { sheet: item.sheet, row: item.row, answer: value });
      const list = items.map((x, k) => (k === index ? { ...x, answer: value } : x));
      setItems(list);
      setHistory((h) => [...h, { index, previous: item.answer }]);
      const next = nextOpen(index, list);
      if (next < 0) say(`Saved ${value}. That was the last one; every row is answered.`);
      else {
        if (!voiceOn.current) note("desk", `Saved “${value}” for ${item.title}.`);
        setIndex(next);
      }
    } catch (e) {
      setError((e as Error).message);
      say("I couldn't save that. The error is on screen.");
    } finally {
      setBusy(false);
    }
  };

  const undo = async () => {
    const last = history[history.length - 1];
    if (!last || !items) return say("Nothing to undo.");
    const target = items[last.index];
    setBusy(true);
    try {
      await post("/admin/review-desk/answer", { sheet: target.sheet, row: target.row, answer: last.previous });
      setItems(items.map((x, k) => (k === last.index ? { ...x, answer: last.previous } : x)));
      setHistory((h) => h.slice(0, -1));
      setIndex(last.index);
      say(`Undone. ${target.title} is back to ${last.previous || "unanswered"}.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const move = (step: number) => items && setIndex((i) => (i + step + items.length) % items.length);

  const stopVoice = useCallback(() => {
    voiceOn.current = false;
    setVoice(false);
    recognition.current?.stop();
    if (canSpeak) window.speechSynthesis.cancel();
  }, []);

  handle.current = (c: Command, said: string) => {
    if (!items || !item) return;
    if (said) note("you", said);
    switch (c.kind) {
      case "answer":
        return void answer(c.value);
      case "next":
        return void move(1);
      case "back":
        return void move(-1);
      case "undo":
        return void undo();
      case "repeat":
        return say(brief(item, index, items.length));
      case "why":
        return say(item.claim + (item.hints.length ? " " + item.hints.join(" ") : ""));
      case "sources":
        return say(sourcesLine(item));
      case "where":
        return say(whereLine(item));
      case "map": {
        const link = safeLink(item.maps_link);
        if (!link) return say("This row has no map link.");
        window.open(link, "_blank", "noopener");
        return say("Opened it in Google Maps.");
      }
      case "progress":
        return say(`${done} of ${items.length} answered, ${items.length - done} to go.`);
      case "jump": {
        const next = nextOpen(index, items);
        return next < 0 ? say("Everything is answered.") : setIndex(next);
      }
      case "help":
        return say(
          `Say yes, no${item.options.includes("closed") ? ", closed" : ""}, skip, back or undo. ` +
            "Ask why, sources, where, or how many left. Say open map, or stop listening.",
        );
      case "stop":
        say("Going quiet. Press V or the mic to wake me.");
        return stopVoice();
    }
  };

  const startVoice = useCallback(() => {
    voiceOn.current = true;
    setVoice(true);
    if (!Recognizer) return;
    if (!recognition.current) {
      const r = new Recognizer();
      r.lang = "en-IN";
      r.continuous = true;
      r.interimResults = true;
      r.onresult = (e) => {
        for (let k = e.resultIndex; k < e.results.length; k++) {
          const text = e.results[k][0].transcript;
          if (speaking.current) continue;
          setHeard(text);
          if (!e.results[k].isFinal) continue;
          setHeard("");
          const command = parseCommand(text);
          if (command) handle.current(command, text.trim());
          else {
            note("you", text.trim());
            say("I didn't catch a command. Say help to hear the options.");
          }
        }
      };
      r.onend = () => {
        if (voiceOn.current && !speaking.current) {
          try {
            r.start();
          } catch {
            /* restarting */
          }
        }
      };
      r.onerror = (e) => {
        if (e.error === "not-allowed" || e.error === "service-not-allowed") {
          setError("Microphone access was blocked. Allow it in the browser to talk to the desk.");
          stopVoice();
        }
      };
      recognition.current = r;
    }
    try {
      recognition.current.start();
    } catch {
      /* already listening */
    }
  }, [say, stopVoice]);

  useEffect(() => () => stopVoice(), [stopVoice]);

  useEffect(() => {
    const keys: Record<string, Command> = {
      a: { kind: "answer", value: "yes" },
      y: { kind: "answer", value: "yes" },
      x: { kind: "answer", value: "no" },
      n: { kind: "answer", value: "no" },
      c: { kind: "answer", value: "closed" },
      s: { kind: "next" },
      arrowright: { kind: "next" },
      arrowleft: { kind: "back" },
      u: { kind: "undo" },
      r: { kind: "repeat" },
      m: { kind: "map" },
    };
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.closest?.("input, textarea, select, [contenteditable]") || e.metaKey || e.ctrlKey || e.altKey) return;
      const key = e.key.toLowerCase();
      if (key === "v") {
        e.preventDefault();
        return voiceOn.current ? stopVoice() : startVoice();
      }
      if (keys[key]) {
        e.preventDefault();
        handle.current(keys[key], "");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [startVoice, stopVoice]);

  if (error && !items) return <ErrorBox message={error} />;
  if (!items) return <Loading label="Opening every row and gathering what I know…" />;
  if (!items.length)
    return <p className="desk-empty">No spot-check sheets found in data/city-collection. Generate them, then come back.</p>;
  if (!item) return null;

  const match = item.matches[0];
  const pct = Math.round((done / items.length) * 100);
  const mapLink = safeLink(item.maps_link);

  return (
    <section className="desk" aria-label="Quick review desk">
      <header className="desk-bar">
        <div className="desk-progress" aria-label={`${done} of ${items.length} answered`}>
          <span className="desk-count">
            {done}
            <small>/{items.length}</small>
          </span>
          <span className="desk-meter">
            <span style={{ width: pct + "%" }} />
          </span>
        </div>
        <span className="desk-sheet">
          {item.sheet === "decisions" ? "My decisions" : "Overture places"} · row {item.row + 1}
        </span>
        <button
          className={"desk-mic" + (voice ? " on" : "")}
          aria-pressed={voice}
          onClick={() => (voice ? stopVoice() : startVoice())}
          title="Talk to the desk (V)"
        >
          <span className="desk-mic-dot" aria-hidden />
          {voice ? (Recognizer ? "Listening" : "Reading aloud") : "Voice"}
        </button>
      </header>

      <div className="desk-grid">
        <article className="desk-card" aria-live="polite">
          <p className="desk-kicker">{item.question}</p>
          <h3>{item.title}</h3>
          <p className="desk-claim">{item.claim}</p>
          {item.hints.length > 0 && (
            <ul className="desk-hints">
              {item.hints.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          )}

          <div className="desk-evidence">
            {match ? (
              <dl>
                <dt>Stored as</dt>
                <dd>{[match.name, match.category, match.status].filter(Boolean).join(" · ")}</dd>
                {(match.area || match.address) && (
                  <>
                    <dt>Where</dt>
                    <dd>{match.address && match.area && match.address.includes(match.area) ? match.address : [match.area, match.address].filter(Boolean).join(" · ")}</dd>
                  </>
                )}
                <dt>Sources</dt>
                <dd>
                  {match.sources.join(", ") || "none named"}
                  {match.corroboration && ` · ${match.corroboration.replace(/_/g, " ")}`}
                </dd>
                {match.websites.length > 0 && (
                  <>
                    <dt>Website</dt>
                    <dd>{match.websites.join(" · ")}</dd>
                  </>
                )}
                {match.search.length > 0 && (
                  <>
                    <dt>Web says</dt>
                    <dd>{match.search.join(" · ")}</dd>
                  </>
                )}
                {match.notes.length > 0 && (
                  <>
                    <dt>Notes</dt>
                    <dd>{match.notes.join(" · ")}</dd>
                  </>
                )}
              </dl>
            ) : (
              <p className="desk-none">Nothing stored under this exact name. The map is searching for it.</p>
            )}
          </div>

          <div className="desk-actions">
            {item.options.map((o) => (
              <button
                key={o}
                className={`desk-answer desk-${o}` + (item.answer === o ? " chosen" : "")}
                disabled={busy}
                onClick={() => answer(o)}
              >
                {ANSWER_LABEL[o]}
                <kbd>{KEYS[o]}</kbd>
              </button>
            ))}
          </div>
          <div className="desk-nav">
            <button onClick={() => move(-1)}>← Back</button>
            <button onClick={() => move(1)}>
              Skip <kbd>S</kbd>
            </button>
            <button onClick={undo} disabled={!history.length || busy}>
              Undo <kbd>U</kbd>
            </button>
            {mapLink && (
              <a href={mapLink} target="_blank" rel="noreferrer">
                Open in Maps <kbd>M</kbd>
              </a>
            )}
          </div>
        </article>

        <div className="desk-side">
          <iframe
            key={item.embed}
            className="desk-map"
            title={`Map of ${item.title}`}
            src={item.embed}
            referrerPolicy="no-referrer"
          />
          <div className="desk-talk" aria-label="Conversation with the desk">
            {log.length === 0 ? (
              <p className="desk-tip">
                Press the mic or <kbd>V</kbd> and just talk: “yes”, “no”, “skip”, “why?”, “sources?”, “where is it?”, “how many
                left?”, “undo”.
                {!Recognizer && " This browser can't listen, so I'll only read rows aloud. Use Chrome or Edge to talk back."}
              </p>
            ) : (
              log.slice(-6).map((l, k) => (
                <p key={log.length - 6 + k} className={"desk-line " + l.who}>
                  {l.text}
                </p>
              ))
            )}
            {heard && <p className="desk-line you live">{heard}…</p>}
          </div>
          {Recognizer && (
            <p className="desk-privacy">Your browser's speech service turns voice into text. Nothing is recorded here.</p>
          )}
        </div>
      </div>
      {items && <ErrorBox message={error} />}
    </section>
  );
}
