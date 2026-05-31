# ClearPath — a voice agent that fills medical intake forms

> Built at the YC Voice Agents Hackathon (Cekura × Daily/Pipecat, with NVIDIA, AWS, Twilio).

---

## 1. What is this?

**ClearPath replaces the medical-intake clipboard with a conversation.**

A patient opens a web intake form (or calls a phone number) and just *talks*. As they
speak, the form fills in **live on screen** — name, date of birth, medications, allergies,
insurance, emergency contact — each field populating and highlighting in real time, read
back for confirmation, and submitted when all required fields are captured.

Two front-ends share **one** voice pipeline:

- **Web** — the voice agent drives a live React intake form using Pipecat 1.3.0's new
  browser-control (UI Agent) protocol. The patient watches fields populate as they talk.
- **Phone** — the same agent answers a Twilio call and completes the entire intake by
  voice, for patients without a smartphone. No screen required.

Completed intakes (web **and** phone) land in a single staff dashboard.

**Why it matters:** US healthcare spends ~$250B/yr on administration, ~2 paperwork hours
per patient-care hour, and ~40% of intake forms come back with errors. ClearPath turns a
frustrating paper process into a ~90-second conversation that produces clean, structured data.

### Pipeline

```
Patient voice
   │
   ▼
[ Browser WebRTC ]  ── or ──  [ Twilio phone call ]
   │                               │
   └───────────────┬───────────────┘
                   ▼
            Pipecat pipeline
   ┌──────────────────────────────────────────────┐
   │  NVIDIA Nemotron Speech Streaming STT   (ears) │
   │  NVIDIA Nemotron-3-Super-120B LLM      (brain) │
   │  Gradium TTS                           (voice) │
   └──────────────────────────────────────────────┘
                   │
   ┌───────────────┴───────────────┐
   ▼                               ▼
fill_form_field()              record_field()
→ RTVI UI commands             → stored server-side
→ React form fills live        → REST API
                   │
                   ▼
        Staff results dashboard (/results)
```

### Tech stack

| Layer | Choice |
|------|--------|
| Orchestration | **Pipecat 1.3.0** (incl. the new UI Agent / browser-control protocol) |
| STT | **NVIDIA Nemotron Speech Streaming** (open weights) |
| LLM | **NVIDIA Nemotron-3-Super-120B** (open weights) |
| TTS | Gradium |
| Telephony | Twilio (Media Streams → Pipecat) |
| Web client | React + Vite + `@pipecat-ai/client-react` + `@pipecat-ai/small-webrtc-transport` |
| Deploy | Pipecat Cloud (Daily transport) |
| Eval / QA | **Cekura** (simulated callers + LLM-judge metrics) |

---

## 2. Demo video (< 60 seconds)

[![Medical Intake Form Demo](https://img.youtube.com/vi/ZxLRi5qF01Y/0.jpg)](https://youtu.be/ZxLRi5qF01Y)


---

## 3. How we used Cekura, Nemotron, and Pipecat

### Pipecat (orchestration + browser control)

Pipecat is the backbone. The interesting part is **Pipecat 1.3.0's UI Agent Protocol**:
the server-side agent drives the patient's browser in real time.

- The React form streams its accessibility tree to the server with `useUISnapshot()`.
- The agent's `fill_form_field` tool pushes `RTVIUICommandFrame`s (`set_input_value`,
  `scroll_to`, `highlight`) downstream; the RTVI observer relays them over WebRTC to the
  browser's `useDefaultUICommandHandlers()`, which fills + flashes the field.
- **No UIWorker subclass needed** — pushing UI command frames straight into the pipeline
  and letting the auto-wired RTVI observer relay them turned out to be the clean path.

The same pipeline runs over **three transports**: SmallWebRTC (local web), Daily (Pipecat
Cloud), and Twilio WebSocket (phone) — selected at runtime from the runner arguments.

### NVIDIA Nemotron (STT + LLM — both open weights)

The entire "ears + brain" of the agent is Nemotron, hosted on AWS:

- **Nemotron Speech Streaming** transcribes the patient over a WebSocket.
- **Nemotron-3-Super-120B** decides which field each answer maps to, calls the
  `fill_form_field` / `record_field` tool, and generates the spoken response — all under
  real-time latency (we measured TTFB ~0.2s to the first answer token).

Nemotron's tool-calling is what makes the live form-fill possible: every patient turn
becomes a structured tool call with the right `field_id` and value.

### Cekura (testing & evaluation) — the heart of the hackathon theme

**What we were trying to accomplish:** prove the agent works under real conditions, not
just a happy-path demo. We wanted automated, adversarial coverage of the failure modes that
actually bite a medical intake bot: long member-ID numbers, spoken-date normalization,
self-corrections, callers who don't have all their info, and adversarial/off-topic callers.

**What we built in Cekura (entirely through the Cekura MCP in Claude Code):**
- Registered the deployed Pipecat agent (`clearpath-intake`).
- Authored **6 custom LLM-judge metrics**: field-capture accuracy, number normalization &
  digit read-back, no cross-field number bleed, turn discipline, completion correctness,
  and "stays on task / no prompt leakage."
- Authored **6 simulated-caller scenarios** (happy path, multi-fact utterance, long member
  ID with pauses, self-correction, unknown optional fields, adversarial caller), each
  scored against all 6 metrics — plus Cekura's free predefined metrics (latency,
  interruption, transcription accuracy, talk ratio).
- Ran the suite against the **live deployed agent** over WebRTC.

**How much it improved performance — the concrete story:** our **first Cekura run failed
every scenario**, and the transcripts showed why: the agent produced **zero turns**. The
cloud logs pinpointed it instantly —

```
ERROR | bot:bot:372 | Unsupported runner type:
        <class 'pipecatcloud.agent.DailySessionArguments'>
```

Our `bot()` only handled SmallWebRTC (local) and Twilio WebSocket — but **Pipecat Cloud
starts sessions as a Daily room**, which we'd never exercised locally. The agent silently
exited on every cloud session. We added a `DailySessionArguments` → `DailyTransport` path,
added the `daily` dependency, redeployed, and re-ran — and the agent went from **0%
(silent on every call)** to conducting full intake conversations end-to-end.

That's the point of Cekura: a bug that was **invisible locally** (where everything worked)
showed up the moment we tested the agent the way it's actually deployed. We would have
demoed a broken cloud agent without it.

---

## 4. What we built **new** during the hackathon

We started from the Pipecat "Field & Flower" flower-shop starter in this repo. Essentially
**everything below was built during the hackathon** — only the AI-service wrappers
(`nemotron_llm.py`, `nvidia_stt.py`) and the project scaffold were borrowed from the starter.

**New backend (`server/`):**
- `bot-intake.py` — the ClearPath web intake agent: 15-field flow, the `fill_form_field` /
  `submit_form` tools that drive the browser via RTVI UI commands, and the system prompt.
- `bot-intake-phone.py` — the Twilio phone-only intake agent (records by voice, no browser).
- `intake_fields.py` — shared 15-field contract (mirrored on the client).
- `number_utils.py` — spoken-number normalization we wrote from scratch:
  "may second two thousand five" → `05/02/2005`, digit-by-digit ID/phone parsing, and a
  `to_spoken()` helper so the agent reads numbers back digit-by-digit instead of as
  "one hundred twenty-three thousand."
- `intake_backend.py` — FastAPI store + REST API for completed intakes.
- Multi-transport `bot()` (SmallWebRTC + Daily + Twilio) and Daily/Pipecat-Cloud deploy.

**New frontend (`client/`):**
- A React intake form styled like a real clinic portal, with a scroll-driven clipboard
  onboarding animation.
- The Pipecat client integration (`useUISnapshot`, `useDefaultUICommandHandlers`), live
  transcript panel, and a `/results` staff dashboard (web + phone records, auto-refresh).

**New eval suite:** the entire Cekura agent, 6 metrics, and 6 scenarios (see
`CEKURA_SCENARIOS.md`, `CEKURA_SETUP.md`).

**Bugs we found and fixed during the build (all new work):**
- Nemotron streamed `<think>` reasoning tokens into spoken content even with thinking
  disabled — we strip them at the chunk level in `nemotron_llm.py` (preserving inter-token
  spaces, which a naive per-frame `.strip()` destroyed → "whatisyourname").
- Twilio audio is 8 kHz but the NVIDIA ASR expects 16 kHz — phone STT returned *nothing*
  until we added a resampler in `nvidia_stt.py`.
- VAD `stop_secs` default (0.2s) cut patients off mid-number; raised to 1.0s so digit-group
  pauses don't split a member ID across two fields.
- The Pipecat-Cloud Daily-transport gap described above (found via Cekura).

---

## 5. Feedback on the tools

### NVIDIA Nemotron

**What it did well**
- **Fast.** TTFB to the first real answer token was ~0.2s in our runs — well within
  real-time voice budget, even for a 120B model.
- **Excellent structured tool-calling.** Mapping free-form patient speech to the correct
  `field_id` + value, turn after turn, was rock-solid — this is what makes the live
  form-fill work at all.
- **Good instruction-following** on tight "one question per turn" constraints.

**What could be better**
- **Thinking tokens leak into content.** With `chat_template_kwargs.enable_thinking=false`,
  the served endpoint still emitted `<think>…</think>` (and stray `</think>`) inside the
  spoken `content`, and exposed no separate `reasoning_content` field — so without a
  reasoning parser on the vLLM side, chain-of-thought gets spoken aloud. We had to strip it
  ourselves at the chunk level. A reliable on/off switch (or always routing reasoning to
  `reasoning_content`) would remove a real footgun for voice.
- **Digit strings.** The model tends to emit IDs/phone numbers as written digits that TTS
  then reads as cardinals ("one hundred twenty-three thousand…"). Not strictly the model's
  fault, but a nudge toward digit-by-digit rendering for ID-like fields would help voice use.

### Cekura

**What worked really well**
- **It caught our most important bug.** The first run immediately surfaced that the
  cloud-deployed agent was silent (Daily transport gap) — something local testing could
  never have shown. That alone justified the tool.
- **MCP-in-Claude-Code workflow is excellent.** Creating the agent, metrics, and scenarios
  and launching live WebRTC runs entirely from the terminal, with transcripts + per-metric
  explanations + recordings coming back, is a great loop.
- **Free predefined metrics** (latency, interruption, transcription accuracy) layered on top
  of our custom ones with zero extra work.

**Bugs / friction we hit**
- **API-key auth.** Two freshly generated dashboard API keys both returned
  `401 Authentication failed` over the MCP (`X-CEKURA-API-KEY`); only OAuth
  (`claude mcp add --transport http`) worked. Worth checking whether newly created keys are
  active by default.
- **MCP env-var substitution.** The plugin's bundled `.mcp.json` reads `${CEKURA_API_KEY}`,
  but the running Claude Code process didn't pick up a freshly-set value across restarts in
  our case — confusing to debug. OAuth sidesteps it; flagging for others.
- **`metrics_create` schema.** `assistant_id` is documented as optional but the API rejects
  a blank string (`"may not be blank"`) — you must omit the field entirely. Easy to trip on.
- **Pipecat provider naming.** `assistant_provider` has no `pipecat` value; Pipecat is
  selected via `transcript_provider: "pipecat"` + `pipecat_api_key` +
  `pipecat_data.pipecat_agent_name`. The docs note it, but the enum mismatch is a stumble.

**On self-improvement loops:** the diagnose → fix → redeploy → re-run loop genuinely worked
for us (silent agent → working agent in one cycle). The thing that would make it *tighter*
is a one-command "re-run this exact run after redeploy" and a built-in run-to-run diff so
you can see a metric move from 0% → N% without eyeballing two reports.

### Pipecat

- **1.3.0 UI Agent Protocol is the star.** Driving a real web form from a server-side voice
  agent, with the accessibility tree as the agent's "eyes," is genuinely novel and worked.
- **Multi-transport is powerful but has sharp edges.** The same bot ran over SmallWebRTC,
  Daily, and Twilio — but the **local vs. cloud transport mismatch** (SmallWebRTC locally,
  `DailySessionArguments` on Pipecat Cloud) is an easy, silent footgun. A louder warning
  when a bot has no handler for the transport it's actually invoked with would help.
- **Packaging nit:** `SmallWebRTCTransport` lives in a separate npm package
  (`@pipecat-ai/small-webrtc-transport`), and `client-react`'s bundled types import from a
  bare `client-js` specifier — needed a `tsconfig` paths alias to resolve.

---

## Repo layout

```
server/
  bot-intake.py          # web intake agent (drives the React form via RTVI UI commands)
  bot-intake-phone.py    # Twilio phone intake agent (voice-only)
  intake_fields.py       # shared 15-field contract
  number_utils.py        # spoken date/number normalization + digit read-back
  intake_backend.py      # FastAPI store + REST API for completed intakes
  nemotron_llm.py        # Nemotron LLM service (+ <think>-token stripping)
  nvidia_stt.py          # Nemotron STT service (+ 8kHz→16kHz resample for telephony)
  PHONE_SETUP.md         # Twilio + ngrok runbook
client/
  src/IntakeForm.tsx     # clinic-styled intake form
  src/VoicePanel.tsx     # Pipecat client + UI command handlers + live transcript
  src/Results.tsx        # staff dashboard (web + phone records)
AGENTS.md                # Cekura agent guide (fields, metrics, IDs)
CEKURA_SCENARIOS.md      # 10 medical-intake test scenarios + metric definitions
CEKURA_SETUP.md          # Cekura runbook (deploy → metrics → scenarios → run → report)
```

## Running it locally

**Web flow** (3 terminals):
```bash
cd server && uv run uvicorn intake_backend:app --port 8000   # API
cd server && ENV=local uv run bot-intake.py                  # web voice bot
cd client && npm run dev                                     # frontend
```
Then: talk at http://localhost:5173 · results at http://localhost:5173/results

**Phone flow:** see `server/PHONE_SETUP.md` (Twilio + ngrok).

**Cekura eval:** see `CEKURA_SETUP.md`.
