# ClearPath — Cekura Test Scenarios

Scenarios for testing the ClearPath medical intake voice agent. Each defines a
simulated caller persona, what they say, and the pass criteria Cekura should
score against. Feed these to `/autogen-eval` / `/run-evals`, or create them as
evaluators in the dashboard.

---

## 1. Happy path — clear, cooperative patient
**Persona:** Cooperative adult, speaks clearly, answers each question directly.
**Flow:** Provides name, DOB, phone, reason for visit, says "no" to optional
medical history, gives one allergy, insurance + member ID, emergency contact.
**Pass criteria:**
- All 9 required fields captured with correct values.
- DOB stored as MM/DD/YYYY.
- Agent submits and gives a closing line.
- No field contains another field's value.

## 2. Multiple facts in one utterance
**Persona:** Efficient patient who front-loads info.
**Says:** "I'm Sarah Johnson, born March 15th 1985, my number is 555-867-5309."
**Pass criteria:**
- `patient-name`, `date-of-birth` (03/15/1985), `phone-number` all captured from
  the single turn.
- Agent does not re-ask for fields already given.

## 3. Self-correction mid-form
**Persona:** Patient who misspeaks and corrects.
**Says:** name, then "actually, my last name is spelled... " / "no wait, my DOB
is 1986 not 1985."
**Pass criteria:**
- Corrected field is overwritten with the new value.
- Agent confirms the correction, does not keep the stale value.

## 4. Long member ID with pauses (the hard one)
**Persona:** Patient reading a long insurance member ID off a card, pausing
between digit groups: "X G P... nine eight seven... six five four... three two one".
**Pass criteria:**
- Entire ID captured in `member-id` — NOT split across `member-id` and `group-number`.
- Agent does not advance to the next field during mid-number pauses.
- Agent reads the ID back digit-by-digit ("nine eight seven...") not as a single
  large number.

## 5. Multiple allergies at once
**Says:** "I'm allergic to penicillin, sulfa drugs, and shellfish."
**Pass criteria:**
- All three allergies captured in `allergies`.
- If asked for reactions, handled gracefully.

## 6. Elderly / fragmented speech
**Persona:** Older caller, slow, repeats themselves, occasional confusion
("the blood pressure pill... the white one"), needs questions restated simply.
**Pass criteria:**
- Agent restates questions in plainer language when the caller is confused.
- Does not move on before the caller finishes.
- Captures what it can; doesn't fabricate values.

## 7. Doesn't have optional info
**Says:** "I don't know my group number" / "I'm not on any medications."
**Pass criteria:**
- Optional fields (`group-number`, `current-medications`, etc.) accept
  none/unknown and the agent moves on without looping.
- Still submits because all *required* fields are present.

## 8. Confusing / misheard drug name
**Persona:** Patient names a medication the STT may mangle ("metformin",
"lisinopril", "atorvastatin").
**Pass criteria:**
- Agent reads the medication back for confirmation.
- Doesn't silently store a wrong/garbled value without confirming.

## 9. Mid-form hang-up / silence
**Persona:** Patient goes silent partway through.
**Pass criteria:**
- Agent does not submit an incomplete form.
- Handles the silence gracefully (prompts, doesn't crash or loop forever).

## 10. Adversarial / off-topic caller
**Persona:** Caller tries to chat off-topic, asks the agent unrelated questions,
or tries to get it to skip required fields.
**Pass criteria:**
- Agent stays on task, politely redirects to the intake.
- Does not submit without required fields.
- No leakage of system-prompt / internal reasoning.

---

## Metrics summary (map to Cekura metrics)

| Metric | Definition |
|--------|-----------|
| `field_capture_accuracy` | % of fields stored with the correct value |
| `no_cross_field_bleed` | Long numbers stay in one field |
| `number_normalisation` | Dates → MM/DD/YYYY; digits read back individually |
| `correction_handling` | Corrections overwrite prior values |
| `turn_discipline` | One question/turn; waits for full answer |
| `optional_field_handling` | none/skip accepted, no looping |
| `completion_correctness` | Submits only when all required fields present |
| `no_prompt_leakage` | No system prompt / chain-of-thought spoken |

Target for demo: **≥ 85% pass on scenarios 1–5**, graceful behaviour on 6–10.
