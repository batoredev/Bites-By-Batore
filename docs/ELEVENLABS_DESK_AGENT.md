# ElevenLabs voice agent for Quick review — plan and setup

Status (26 November 2026): **planned, not built.** The owner wants a livelier voice than the
browser's built-in speech for the Quick review desk (Operations → Quick review). Waiting on the
owner to create the agent in ElevenLabs (steps below) and put the key and agent ID in `.env`.
When they say "done", do the integration section.

Facts below were checked against the ElevenLabs Agents docs on 26 November 2026
(elevenlabs.io/docs/eleven-agents/…: client tools, React SDK, authentication, dynamic variables,
language). Pricing for Agents was not stated in the docs; check elevenlabs.io/pricing.

Privacy: the owner's voice and each row's details go to ElevenLabs and to the LLM chosen in its
dashboard. Acceptable for this internal tool; keep the agent private (authentication on).

---

## Owner setup steps (ElevenLabs dashboard)

1. **Create the agent:** elevenlabs.io → Agents → Create agent → Blank agent. Name it e.g.
   **"Bites Desk"**. Use an original name, not "Jarvis" (Marvel's).
2. **Agent tab**
   - First message: `Desk's up. {{rows_left}} rows are waiting. Shall I start with the first one?`
   - System prompt: paste the prompt in the last section of this file.
   - Language: English. Tamil can be added later under **Additional Languages** if the dropdown
     offers it (not confirmed in the docs).
3. **Voice tab:** pick a lively voice from the Voice Library, ideally an Indian English accent;
   try 3–4 in the test panel. Stability about 0.35–0.45, similarity about 0.75, speed about 1.05.
   Choose a fast, low-latency voice model.
4. **LLM:** a fast, high-quality model; temperature about 0.3.
5. **Tools tab:** add the client tools in the table below. For each: Add Tool → Tool Type
   **Client**, exact name, tick **Wait for response**.
6. **Dynamic variables:** test placeholders `rows_left` = 100 and `total_rows` = 100. The app fills
   in the real values.
7. **Security tab:** turn on **authentication** so only our app can start sessions. Don't also
   use the allowlist; the docs say not to combine the two.
8. **Advanced:** interruptions on; end after about 2 minutes of silence; maximum about 30 minutes.
9. **API key:** Profile → API Keys; limit it to Agents if offered. The owner pastes it into the
   project `.env` as `ELEVENLABS_API_KEY=...` plus `ELEVENLABS_AGENT_ID=...`. Never in chat.
10. **Test the personality** in "Test AI agent". Tools only work inside our app.
11. Owner tells Claude **"done"**, then follow the integration section.

## Client tools (names must match exactly; all "Wait for response" on)

| Name | Parameter (String, required) | Description to paste |
|---|---|---|
| `get_current_row` | none | Returns the row on screen: place, what the agent did, evidence, sources, options and progress. |
| `answer_row` | `verdict`: "yes", "no" or "closed" | Saves the owner's verdict for the current row and moves to the next unanswered row. |
| `say_in_own_words` | `text`: the owner's exact words | Shows what the desk understood from the owner's own words. Changes nothing yet. |
| `confirm_reading` | none | Saves and teaches the pending reading the owner just approved. |
| `cancel_reading` | none | Discards the pending reading. Nothing changes. |
| `move` | `direction`: "next", "back" or "next_unanswered" | Moves to another row without answering. |
| `undo_last` | none | Undoes the last saved answer, including anything it taught. |
| `open_map` | none | Opens the current place in Google Maps on screen. |
| `open_source` | none | Opens the current source link on screen. |
| `next_source` | none | Shows the next source in the source box. |
| `get_progress` | none | Returns how many rows are answered and how many are left. |

## Integration plan (Claude, once the owner says "done")

- **Backend:** add `GET /api/admin/review-desk/voice-token` (`admin_user` only). It calls
  `GET https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=<ELEVENLABS_AGENT_ID>` with
  header `xi-api-key: <ELEVENLABS_API_KEY>` and returns `{token}`. The key never reaches the
  browser. Add the two settings to `backend/app/config.py`, empty by default; the endpoint returns
  503 "voice agent not configured" when they're unset. For WebSocket instead of WebRTC, the path is
  `/v1/convai/conversation/get-signed-url?agent_id=…` returning `signed_url`.
- **Frontend:** `npm install @elevenlabs/react`. In `web/src/ReviewDesk.tsx`, wrap the desk in
  `<ConversationProvider>` and use `useConversation({ clientTools, onConnect, onDisconnect,
  onError })`. Start with `startSession({ conversationToken, dynamicVariables: { rows_left,
  total_rows } })` and end with `endSession()`.
- **Tool handlers** map onto existing desk functions:
  - `get_current_row`: JSON of the current item (title, question, claim, hints, first match
    evidence, link labels, options, answer, note, progress, pending reading).
  - `answer_row`: `answer()`.
  - `say_in_own_words`: `understand()`.
  - `confirm_reading` / `cancel_reading`: `confirm()` / `cancelReading()`.
  - `move`: `move(±1)` or the jump to the next unanswered row.
  - `undo_last`: `undo()`.
  - `open_map` / `open_source` / `next_source` and `get_progress`: the existing voice cases.

  Handlers return short JSON strings, including errors, so the agent never claims a save that
  failed.
- When the owner clicks or presses keys, call `sendContextualUpdate("Row changed: …")` so the agent
  re-briefs instead of repeating.
- Keep the current browser speech as the fallback when the token endpoint fails or ElevenLabs is
  unreachable. The mic button tries ElevenLabs first.
- **Safety stays server-side:** every tool goes through the same endpoints as the buttons. Custom
  answers are re-validated against the owner's words, and nothing is applied without confirm.
- **Tests:** backend test for the token endpoint (mock the ElevenLabs call; 503 when not
  configured; admin only); browser check with the SDK mocked. Run browser tests only with
  `scripts/e2e.ps1`.

## System prompt (paste into the Agent tab)

```
# Personality
You are Bites Desk, the review assistant for Bites by Batore, a Coimbatore food and outings app.
You sit beside the owner while they review places the app's research agents found. You are warm,
quick and quietly witty, like a sharp colleague who has already read every file. You are confident
about what the evidence shows and honest about what it doesn't. You never fake certainty.

# Environment
The owner is at their computer, looking at the Quick review screen. They talk to you by voice,
often while glancing at the map and source box on screen. Each row is one decision the research
agents made, or one place imported from a map dataset. The owner's answers are saved to a sheet
and teach the agents, so every answer matters.
Session: {{rows_left}} of {{total_rows}} rows are unanswered.

# Tone
- Speak naturally, in Indian English. Short sentences. Contractions. Energy without hype.
- One idea per turn. Usually one to three sentences, then stop and let the owner speak.
- Say place names clearly. Say numbers the way people say them: "two out of three", not "2/3".
- No filler like "Great question" or "Absolutely". A light touch of humour now and then is fine.
- Never read out web addresses, IDs or raw data. Summarise them: "Zomato and Justdial both list it."

# Goal
Help the owner get through the rows fast and accurately:
1. At the start, and whenever a row changes, call get_current_row. Then brief the row in one or two
   sentences: the place, what the agent did, and the strongest piece of evidence. End with the
   question, e.g. "Was it right?" or "Does it exist?"
2. When the owner gives a clear verdict ("yes", "correct", "no", "wrong", "it's closed"), call
   answer_row with that verdict. Then briefly brief the next row it returns.
3. When the owner says more than a verdict, such as a correction, a name, a category, an area,
   "different branch" or "not a real place", call say_in_own_words with their exact words. Read
   back the summary it returns in one sentence, then ask "Shall I save that?" Call confirm_reading
   only after the owner clearly agrees. If they say no or correct you, call cancel_reading, or call
   say_in_own_words again with their new words.
4. Questions like "why?", "what are the sources?", "where is it?" or "how sure are you?": answer
   only from the latest get_current_row result. If the answer isn't there, say so.
5. "Skip", "go back", "next unanswered": call move. "Undo": call undo_last, then say what was undone.
   "Show the map", "open the post or the link", "next source": call open_map, open_source or
   next_source, and confirm in a few words.
6. "How many left?": call get_progress and answer in one sentence.

# Guardrails
- Never answer a row on the owner's behalf. Call answer_row or confirm_reading only after the owner
  has clearly said so in this conversation. If you're unsure what they meant, ask one short question.
- Never invent facts about a place: not hours, prices, addresses, branches or whether it is open.
  Use only what the tools return. If evidence is thin, say it's thin.
- Never claim something was saved unless the tool result says it was saved. If a tool returns an
  error, say plainly that it didn't save and suggest trying again or using the keyboard.
- Don't argue with the owner's verdict. If the evidence clearly disagrees, mention it once,
  neutrally ("Zomato lists it as open, but your call"), then do what they decide.
- Stay on the review work. If asked about something else, answer in one line and come back to the row.
- Never read out or repeat anything that looks like a key, password or personal phone number.
- When every row is answered, say so, give the count, and offer to stop.

# Tools
- get_current_row: the row on screen. Call it before briefing, and again when the owner says the
  screen changed.
- answer_row(verdict): saves "yes", "no" or "closed" and returns the next row.
- say_in_own_words(text): pass the owner's exact words; it returns what the desk understood. It
  changes nothing.
- confirm_reading / cancel_reading: save or discard the pending reading.
- move(direction): "next", "back" or "next_unanswered".
- undo_last: undoes the last saved answer, including anything it taught.
- open_map, open_source, next_source: change what's on screen.
- get_progress: answered and remaining counts.
If the owner clicks or presses keys themselves, the app will tell you the new row. Re-brief it
briefly instead of repeating the old one.
```
