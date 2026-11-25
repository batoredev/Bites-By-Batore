// Spoken phrases the Quick review desk understands, kept separate so they can be tested without a browser.

export type Command =
  | { kind: "answer"; value: "yes" | "no" | "closed" }
  | {
      kind: "next" | "back" | "undo" | "repeat" | "why" | "sources" | "where" | "map" | "progress" | "jump" | "stop" | "help";
    };

const WORDS: [RegExp, Command][] = [
  [/\b(stop listening|go quiet|pause|sleep)\b/, { kind: "stop" }],
  [/\b(undo|take (that|it) back|revert)\b/, { kind: "undo" }],
  [/\b(closed|shut down|shut|not open anymore)\b/, { kind: "answer", value: "closed" }],
  [/\b(no|nope|reject|wrong|disagree|incorrect|not right)\b/, { kind: "answer", value: "no" }],
  [/\b(yes|yeah|yep|approve|approved|correct|right|agree|looks good|confirm)\b/, { kind: "answer", value: "yes" }],
  [/\b(open (the )?map|show (the )?map|google maps)\b/, { kind: "map" }],
  [/\b(sources?|evidence|proof|details|tell me more)\b/, { kind: "sources" }],
  [/\b(where|address|location|area)\b/, { kind: "where" }],
  [/\b(why|explain|what did you do|reason)\b/, { kind: "why" }],
  [/\b(how many|progress|status|left|remaining)\b/, { kind: "progress" }],
  [/\b(unanswered|jump|pending)\b/, { kind: "jump" }],
  [/\b(skip|next|later)\b/, { kind: "next" }],
  [/\b(back|previous|go back)\b/, { kind: "back" }],
  [/\b(repeat|again|say that)\b/, { kind: "repeat" }],
  [/\b(help|commands|what can i say)\b/, { kind: "help" }],
];

/** Turn a spoken phrase into one desk command. Order matters: "not right" must win over "right". */
export function parseCommand(said: string): Command | null {
  const text = said.toLowerCase().trim();
  for (const [pattern, command] of WORDS) if (pattern.test(text)) return command;
  return null;
}
