import { test, expect } from "@playwright/test";
import { parseCommand } from "../src/voiceCommands";

test("desk voice phrases map to the right command", () => {
  const cases: [string, unknown][] = [
    ["Yes", { kind: "answer", value: "yes" }],
    ["yeah looks good", { kind: "answer", value: "yes" }],
    ["that's not right", { kind: "answer", value: "no" }],
    ["no", { kind: "answer", value: "no" }],
    ["it's closed now", { kind: "answer", value: "closed" }],
    ["skip this one", { kind: "next" }],
    ["go back", { kind: "back" }],
    ["undo that", { kind: "undo" }],
    ["why did you do that", { kind: "why" }],
    ["what are the sources", { kind: "sources" }],
    ["where is it", { kind: "where" }],
    ["how many left", { kind: "progress" }],
    ["open the map", { kind: "map" }],
    ["stop listening", { kind: "stop" }],
    ["open the post", { kind: "openSource" }],
    ["show this source", { kind: "openSource" }],
    ["next source", { kind: "nextSource" }],
    ["show me another post", { kind: "nextSource" }],
    ["next", { kind: "next" }],
    ["banana", null],
  ];
  for (const [said, expected] of cases) expect(parseCommand(said), said).toEqual(expected);
});
