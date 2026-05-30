# ClearPath — Cekura Setup Runbook (Person 3)

Cekura tests the intake agent by running simulated callers against it and scoring
the transcripts. Cekura's automated Pipecat integration connects through
**Pipecat Cloud**, so the flow is: deploy the bot → point Cekura at it →
generate + run scenarios → read the report.

Everything code-side is already done (Dockerfile, `pcc-deploy.toml`, `AGENTS.md`,
`CEKURA_SCENARIOS.md`). The steps below need your accounts and are done once.

---

## Step 1 — Deploy the intake bot to Pipecat Cloud

The Pipecat CLI (`pc`) is already installed.

```bash
cd /Users/sohumdesai/Desktop/yc-hack/server

# 1a. Log in (opens a browser — uses your Pipecat Cloud account)
pc cloud auth login

# 1b. Get your org name (needed later)
pc cloud organizations list

# 1c. Upload secrets from .env (Gradium key, NVIDIA URLs, Twilio creds)
pc cloud secrets set clearpath-intake-secrets --file .env

# 1d. Build + deploy (Dockerfile already points at bot-intake.py)
pc cloud deploy
```

The deploy uses `pcc-deploy.toml` → agent name **`clearpath-intake`**.
`_post_intake` failing in the cloud is harmless (it just logs a warning); Cekura
scores the conversation, not the form POST.

## Step 2 — Get your Cekura API key

1. Sign in at **https://dashboard.cekura.ai**
2. **Settings → API Keys** → create a key
3. Add it to your shell and reload:
   ```bash
   echo 'export CEKURA_API_KEY="ck_your_key_here"' >> ~/.zshrc
   source ~/.zshrc
   ```

## Step 3 — Install the Cekura Claude Code plugin

In Claude Code:
```
/plugin marketplace add cekura-ai/cekura-skills
/plugin install cekura@cekura-skills
```
Then restart, and configure the MCP:
```
/setup-mcp
```

## Step 4 — Create the Cekura agent (provider = Pipecat)

In the Cekura dashboard (or via the MCP), create an agent:
- **Provider**: `Pipecat`
- **Pipecat Cloud API key**: from `pc cloud` (Settings/API in Pipecat Cloud)
- **Agent name**: `clearpath-intake`
- **Agent Configuration (JSON)** — the start-endpoint request body:
  ```json
  { "createDailyRoom": true }
  ```
- **Room Properties (JSON)**:
  ```json
  { "properties": { "enable_prejoin_ui": false } }
  ```

Then copy the **Agent ID** and **Project ID** into `AGENTS.md` (the
"Project-specific details" section).

## Step 5 — Generate scenarios and run

From Claude Code, with the plugin installed and `CEKURA_API_KEY` set:

```
/autogen-eval        # generate evaluators (uses AGENTS.md + CEKURA_SCENARIOS.md)
/run-evals           # run them against clearpath-intake
/cekura-report       # full report: transcripts, scores, failures
```

Or drive it conversationally (the docs' recommended entry point):
> "Use the Cekura MCP to list my agents, then use the Cekura skill to generate
> evaluators for clearpath-intake from CEKURA_SCENARIOS.md and run them."

## Step 6 — Iterate

Read the failures in `/cekura-report`. The likely tuning knobs:
- Field-capture / cross-field bleed → system prompt in `bot-intake.py`
  (FIELD ORDER + LONG NUMBERS sections) and `number_utils.py`.
- Turn discipline / mid-number cutoffs → VAD `stop_secs` in `bot-intake.py`.
- Re-deploy after changes: `pc cloud deploy`, then re-run `/run-evals`.

**Demo target:** ≥ 85% pass on the happy-path scenarios (1–5 in
`CEKURA_SCENARIOS.md`), graceful behaviour on the edge cases (6–10).

---

## Alternative: phone testing (no cloud deploy)

If you'd rather test the **phone** agent over the existing Twilio number, Cekura
can place outbound calls to it. Point a Cekura phone test at your Twilio number
while `bot-intake-phone.py` runs (via ngrok, per `server/PHONE_SETUP.md`). The
automated Pipecat-Cloud path above is cleaner and is the recommended route.
