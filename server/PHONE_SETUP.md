# ClearPath Phone Intake — Twilio Setup

The phone bot (`bot-intake-phone.py`) lets patients complete intake by calling a
Twilio number — no browser. Same NVIDIA Nemotron STT/LLM + Gradium TTS pipeline
as the web bot; records are saved to the intake API and show up in `/results`.

## Local testing (no phone needed)

```bash
# Terminal 1 — intake API
uv run uvicorn intake_backend:app --port 8000

# Terminal 2 — phone bot over WebRTC (test page)
ENV=local uv run bot-intake-phone.py
```

Open http://localhost:7860, click Connect, and talk — the conversation flow is
identical to the real phone path. Completed intakes appear at
http://localhost:5173/results (with a "📞 Phone" tag).

## Production: wire a real Twilio number

1. Deploy the phone bot to Pipecat Cloud (`pc cloud deploy`) as a service named
   e.g. `clearpath-phone`. Get your org name with `pc cloud organizations list`.

2. In the Twilio console, create a **TwiML Bin**:

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Connect>
       <Stream url="wss://api.pipecat.daily.co/ws/twilio">
         <Parameter name="_pipecatCloudServiceHost"
           value="clearpath-phone.YOUR_ORG_NAME"/>
       </Stream>
     </Connect>
   </Response>
   ```

3. Attach the TwiML Bin to your Twilio phone number:
   Phone Numbers → your number → Voice Configuration →
   "A call comes in" → TwiML Bin → select the bin → Save.

4. Call the number. The bot answers and walks the caller through intake.

## Notes

- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env` are used to look up caller
  info; they're already set.
- Twilio media is 8 kHz μ-law — the bot auto-detects the WebSocket transport and
  switches sample rates (see the `WebSocketRunnerArguments` branch in `bot()`).
- The phone bot uses `record_field` (server-side storage) instead of the web
  bot's `fill_form_field` (which drives the browser form). Everything else —
  number normalisation, thinking-token stripping, VAD tuning — is shared.
