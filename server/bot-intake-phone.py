"""ClearPath — Twilio phone-only intake bot.

A patient dials the Twilio number and completes the intake form entirely by
voice — no browser. Same NVIDIA Nemotron STT → Nemotron LLM → Gradium TTS
pipeline as bot-intake.py, but instead of driving a web form it records each
field server-side and POSTs the finished record to the intake API.

Run locally for testing (SmallWebRTC at http://localhost:7860):
    uv run bot-intake-phone.py
"""

import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndTaskFrame, FunctionCallResultProperties, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments, WebSocketRunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.workers.runner import WorkerRunner

from intake_fields import INTAKE_FIELDS, REQUIRED_FIELDS
from nemotron_llm import VLLMOpenAILLMService
from number_utils import normalise_field, to_spoken
from nvidia_stt import NVidiaWebSocketSTTService

load_dotenv(override=True)

INTAKE_API_URL = os.getenv("INTAKE_API_URL", "http://localhost:8000")


async def _post_intake(session_id: str, fields: dict) -> None:
    """POST completed intake to backend API (best-effort — never raises)."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{INTAKE_API_URL}/api/intake",
                json={
                    "session_id": session_id,
                    "fields": fields,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "phone",
                },
            )
    except Exception as exc:
        logger.warning(f"Intake API post failed (non-fatal): {exc}")


async def run_bot(
    transport: BaseTransport,
    from_number: str | None = None,
    audio_in_sample_rate: int = 16000,
    audio_out_sample_rate: int = 24000,
) -> None:
    logger.info("Starting ClearPath phone intake bot")

    session_id = f"phone-{datetime.utcnow().strftime('%H%M%S')}"
    collected: dict[str, str] = {}

    # ── Tool functions ────────────────────────────────────────────────────

    async def record_field(
        params: FunctionCallParams,
        field_id: str,
        value: str,
    ) -> None:
        """Record a single intake field answered by the patient over the phone.

        Call this immediately after the patient provides each piece of
        information — one call per field, even if they give several at once.

        Args:
            field_id: Field identifier matching the intake form.
            value: The value as understood from patient speech.
        """
        logger.info(f"[RECORD] record_field: field_id={field_id!r} raw_value={value!r}")

        if field_id not in INTAKE_FIELDS:
            logger.warning(f"[RECORD] Unknown field_id {field_id!r} — skipping")
            await params.result_callback({"ok": False, "reason": f"Unknown field_id: {field_id!r}"})
            return

        value = normalise_field(field_id, value)
        collected[field_id] = value
        spoken_value = to_spoken(field_id, value)
        logger.info(f"[RECORD] Done: {field_id!r} = {value!r} (spoken: {spoken_value!r}) | collected: {list(collected.keys())}")
        await params.result_callback(
            {"ok": True, "field_id": field_id, "value": value, "say_back_as": spoken_value}
        )

    async def submit_intake(params: FunctionCallParams) -> None:
        """Submit the completed intake. Only call after all required fields are confirmed."""
        missing = [f for f in REQUIRED_FIELDS if f not in collected]
        if missing:
            await params.result_callback({"ok": False, "missing_required": missing})
            return
        await _post_intake(session_id, collected)
        logger.info(f"Phone intake submitted: session={session_id} collected={collected}")
        await params.result_callback({"ok": True, "session_id": session_id})

    async def end_call(params: FunctionCallParams) -> None:
        """End the call. Only call after saying goodbye to the patient."""
        logger.info("end_call — pushing EndTaskFrame")
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        await params.result_callback(
            {"ok": True}, properties=FunctionCallResultProperties(run_llm=False)
        )

    tool_functions = [record_field, submit_intake, end_call]
    tools = ToolsSchema(standard_tools=tool_functions)

    # ── System prompt ─────────────────────────────────────────────────────

    fields_list = "\n".join(f"  - {fid}: {desc}" for fid, desc in INTAKE_FIELDS.items())
    required_list = ", ".join(REQUIRED_FIELDS)

    system_instruction = f"""You are ClearPath, a medical intake assistant for Valley Medical Center.
The patient is calling by PHONE to complete their pre-visit intake form. They cannot see a screen.
Collect each field by voice, one at a time.

FIELDS (use exact field_id when calling record_field):
{fields_list}

REQUIRED fields: {required_list}

=== STRICT TURN RULES ===
Each of your turns must follow this exact pattern:
  STEP 1: If the patient just answered → call record_field(field_id, value) for that answer.
  STEP 2: Speak ONE short sentence (the next question OR a brief confirmation + next question).
  STEP 3: STOP. Do not ask multiple questions. Do not record fields you haven't asked about yet.

Never record a field before asking the patient for it.
Never ask two questions in the same turn.
Never generate more than 2 sentences total per turn.

FIELD ORDER:
1. patient-name → 2. date-of-birth → 3. phone-number → 4. reason-for-visit →
5. medical-conditions → 6. current-medications → 7. medication-dosages →
8. allergies → 9. allergy-reactions → 10. insurance-provider → 11. member-id →
12. group-number → 13. emergency-name → 14. emergency-relationship → 15. emergency-phone

OPTIONAL fields (6,7,9,12): if patient says "none", "no", "skip" → call record_field(field_id, "none") and move on.

LONG NUMBERS (member-id, group-number, phone numbers):
- These can be long. The patient may pause between groups of digits — that does NOT mean they are finished.
- After they give a number, READ IT BACK and ask "Did I get that right?" before moving to the next field.
- When you read a number back, say it using the "say_back_as" value from the tool result (digits spoken one at a time), not as a single large number.
- If they say it's wrong or give more digits, call record_field again with the corrected/complete value.
- Only advance to the next field once they confirm the number is correct.

WHEN ALL REQUIRED FIELDS ARE FILLED:
→ Call submit_intake.
→ Say "Your intake is complete. Thank you, see you at your appointment!"
→ Call end_call.

VOICE STYLE:
- Short sentences only. No filler words. No "Great!", "Absolutely!", "Of course!".
- This is a phone call — speak clearly and simply. Restate questions in plainer words if the patient seems confused.
- Store dates exactly as spoken: "May 15 1990". Store phone numbers as spoken: "555 867 5309".
"""

    # ── Services ──────────────────────────────────────────────────────────

    stt = NVidiaWebSocketSTTService(
        url=os.getenv("NVIDIA_ASR_URL", "ws://44.241.251.184:8080"),
        strip_interim_prefix=True,
    )

    enable_thinking = os.getenv("NEMOTRON_ENABLE_THINKING", "false").lower() == "true"
    llm = VLLMOpenAILLMService(
        api_key=os.getenv("NEMOTRON_LLM_API_KEY", "EMPTY"),
        base_url=os.getenv(
            "NEMOTRON_LLM_URL",
            "http://nemotron-fleet-alb-1322439314.us-west-2.elb.amazonaws.com/v1",
        ),
        settings=VLLMOpenAILLMService.Settings(
            model=os.getenv("NEMOTRON_LLM_MODEL", "nvidia/nemotron-3-super"),
            system_instruction=system_instruction,
            extra={"extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}}},
        ),
    )

    tts = GradiumTTSService(
        api_key=os.environ["GRADIUM_API_KEY"],
        settings=GradiumTTSService.Settings(
            voice=os.getenv("GRADIUM_VOICE_ID") or "Eu9iL_CYe8N-Gkx_",
        ),
    )

    for fn in tool_functions:
        llm.register_direct_function(fn)

    # Same VAD tuning as the web bot: long stop_secs so patients reciting long
    # member IDs / phone numbers aren't cut off mid-number.
    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(confidence=0.7, start_secs=0.2, stop_secs=1.0, min_volume=0.6)
    )

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=vad_analyzer),
    )

    pipeline = Pipeline([
        transport.input(),
        stt,
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=audio_in_sample_rate,
            audio_out_sample_rate=audio_out_sample_rate,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Patient connected (from: {from_number})")
        context.add_message({
            "role": "user",
            "content": (
                "The patient just called in to complete their intake by phone. "
                "Greet them warmly as ClearPath from Valley Medical Center, and "
                "ask for their full legal name to get started."
            ),
        })
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Patient disconnected")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments) -> None:
    """Entry point — selects transport based on runner arguments."""
    from_number: str | None = None
    transport_overrides: dict = {}

    if os.environ.get("ENV") != "local":
        from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter
        krisp_filter = KrispVivaFilter()
    else:
        krisp_filter = None

    match runner_args:
        case SmallWebRTCRunnerArguments():
            webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection
            transport = SmallWebRTCTransport(
                webrtc_connection=webrtc_connection,
                params=TransportParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                ),
            )
        case WebSocketRunnerArguments():
            # Twilio media streams are 8 kHz μ-law in both directions.
            transport_overrides["audio_in_sample_rate"] = 8000
            transport_overrides["audio_out_sample_rate"] = 8000
            _, call_data = await parse_telephony_websocket(runner_args.websocket)
            serializer = TwilioFrameSerializer(
                stream_sid=call_data["stream_id"],
                call_sid=call_data["call_id"],
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            )
            transport = FastAPIWebsocketTransport(
                websocket=runner_args.websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_in_filter=krisp_filter,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    serializer=serializer,
                ),
            )
        case _:
            logger.error(f"Unsupported runner type: {type(runner_args)}")
            return

    await run_bot(transport, from_number=from_number, **transport_overrides)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
