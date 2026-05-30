# ClearPath — Cekura Testing Guide

This file teaches AI coding agents (and the Cekura MCP/skills) how to evaluate
the **ClearPath medical intake voice agent** with Cekura.

## What the agent does

ClearPath is a voice agent that completes a patient pre-visit intake form by
conversation. It collects 15 fields one at a time, normalises spoken numbers
(dates → MM/DD/YYYY, phone/ID digits), reads them back for confirmation, and
submits when all required fields are captured. Two front-ends share the same
Nemotron pipeline:
- **Web** (`bot-intake.py`): fills a live React form via Pipecat UI commands.
- **Phone** (`bot-intake-phone.py`): collects everything by voice over Twilio.

Pipeline: NVIDIA Nemotron Speech Streaming STT → Nemotron-3-Super-120B LLM →
Gradium TTS.

## Connecting to Cekura (MCP)

The Cekura MCP is configured via `/setup-mcp` after installing the plugin.
Auth uses the `CEKURA_API_KEY` env var (Settings → API Keys in the dashboard).

## Project-specific details

- **Organization**: `ychacks` (ID 4892)
- **Project**: `Sohum Desai Project` (ID 5945)
- **Agent ID**: `18090`
- **Default personality ID**: `693`
- **Provider**: `Pipecat`
- **Pipecat Cloud agent name**: `clearpath-intake` (deployed, Ready)
- **Pipecat Cloud region**: us-west

## The 15 intake fields

| field_id | what it captures | type |
|----------|------------------|------|
| patient-name | full legal name | text |
| date-of-birth | DOB → MM/DD/YYYY | normalised |
| phone-number | phone | normalised digits |
| reason-for-visit | reason for today's visit | text |
| medical-conditions | existing conditions | text (optional) |
| current-medications | medications | text (optional) |
| medication-dosages | dosages | text (optional) |
| allergies | drug/food allergies | text |
| allergy-reactions | reaction types | text (optional) |
| insurance-provider | insurer | text |
| member-id | insurance member ID | normalised digits |
| group-number | insurance group number | normalised digits (optional) |
| emergency-name | emergency contact name | text |
| emergency-relationship | relationship | text |
| emergency-phone | emergency phone | normalised digits |

Required: patient-name, date-of-birth, phone-number, reason-for-visit,
allergies, insurance-provider, member-id, emergency-name, emergency-phone.

## Key metrics to evaluate

1. **Field capture accuracy** — every answer lands in the correct field with the
   correct value (no cross-field bleed, especially for long numbers).
2. **Number normalisation** — "may second two thousand five" → `05/02/2005`;
   spoken digit strings stored compactly; read back digit-by-digit (not as a
   cardinal number).
3. **Turn discipline** — one question per turn, waits for the full answer, does
   not advance mid-number when the caller pauses between digit groups.
4. **Correction handling** — when the patient corrects a value, the field is
   overwritten with the new value.
5. **Optional-field handling** — "none"/"skip" is accepted and the agent moves on.
6. **Completion** — submits only after all required fields are confirmed; reads a
   clear closing line.

## Scenarios

See `CEKURA_SCENARIOS.md` for the full test scenario set (happy path,
corrections, long member IDs, elderly/fragmented speech, missing info,
multilingual drug names, mid-form hang-up).

## Common workflows

- **Generate evaluators from the field/metric list**: `/autogen-eval`
- **Run the scenarios**: `/run-evals`
- **Full quality report**: `/cekura-report`
- **Create/update a metric**: `/create-metric`
