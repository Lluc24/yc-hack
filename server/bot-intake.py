"""ClearPath — medical intake voice agent.

Pipeline: NVIDIA Nemotron STT → Nemotron-3-Super LLM → Gradium TTS.

Tool functions push RTVIUICommandFrame frames downstream so the RTVI observer
(auto-wired by PipelineWorker) sends set_input_value / highlight / click
commands to the React intake form in real time.

Run locally:
    uv run bot-intake.py
"""

import os
import re
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
from pipecat.processors.frameworks.rtvi import RTVIUICommandFrame
from pipecat.processors.frameworks.rtvi.models import Click, Highlight, ScrollTo, SetInputValue
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments, WebSocketRunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
from pipecat.turns.user_turn_strategies import FilterIncompleteUserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from intake_fields import INTAKE_FIELDS, REQUIRED_FIELDS
from nemotron_llm import VLLMOpenAILLMService
from nvidia_stt import NVidiaWebSocketSTTService
from number_utils import normalise_field, to_spoken

load_dotenv(override=True)

INTAKE_API_URL = os.getenv("INTAKE_API_URL", "http://localhost:8000")

# NOTE: Thinking-token (<think>...</think>) and ✓-marker stripping happens at the
# chunk level inside VLLMOpenAILLMService.get_chat_completions (nemotron_llm.py),
# BEFORE Pipecat aggregates tokens into TextFrames. Doing it there preserves the
# leading spaces on each streamed token. A pipeline-level processor that ran
# .strip() per TextFrame would collapse "what is the name" into "whatisthename".


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
                },
            )
    except Exception as exc:
        logger.warning(f"Intake API post failed (non-fatal): {exc}")


async def run_bot(
    transport: BaseTransport,
    audio_in_sample_rate: int = 16000,
    audio_out_sample_rate: int = 24000,
) -> None:
    logger.info("Starting ClearPath intake bot")

    session_id = f"intake-{datetime.utcnow().strftime('%H%M%S')}"
    collected: dict[str, str] = {}

    # ── Tool functions ────────────────────────────────────────────────────

    async def fill_form_field(
        params: FunctionCallParams,
        field_id: str,
        value: str,
    ) -> None:
        """Fill a single intake form field and highlight it on screen.

        Call this immediately after the patient provides each piece of
        information — one call per field, even if they give multiple facts
        in one sentence.

        Args:
            field_id: HTML element id of the target field. Must be one of
                the known field IDs listed in the system prompt.
            value: The exact value to enter, as understood from patient speech.
        """
        logger.info(f"[FILL] fill_form_field called: field_id={field_id!r} raw_value={value!r}")

        if field_id not in INTAKE_FIELDS:
            logger.warning(f"[FILL] Unknown field_id {field_id!r} — skipping")
            await params.result_callback({"ok": False, "reason": f"Unknown field_id: {field_id!r}"})
            return

        # Normalise spoken numbers/dates to proper formats
        value = normalise_field(field_id, value)
        logger.info(f"[FILL] normalised value: {value!r}")

        set_cmd = SetInputValue(target_id=field_id, value=value)
        scroll_cmd = ScrollTo(target_id=field_id)
        highlight_cmd = Highlight(target_id=field_id)

        logger.debug(f"[FILL] Pushing set_input_value: {set_cmd.model_dump()}")
        await params.llm.push_frame(
            RTVIUICommandFrame(command="set_input_value", payload=set_cmd.model_dump()),
            FrameDirection.DOWNSTREAM,
        )
        await params.llm.push_frame(
            RTVIUICommandFrame(command="scroll_to", payload=scroll_cmd.model_dump()),
            FrameDirection.DOWNSTREAM,
        )
        await params.llm.push_frame(
            RTVIUICommandFrame(command="highlight", payload=highlight_cmd.model_dump()),
            FrameDirection.DOWNSTREAM,
        )

        collected[field_id] = value
        # The form displays the compact value, but tell the LLM a TTS-friendly
        # version (digits spaced out) so when it reads the value back it says
        # "one two three four five six", not "one hundred twenty-three thousand".
        spoken_value = to_spoken(field_id, value)
        logger.info(f"[FILL] Done: {field_id!r} = {value!r} (spoken: {spoken_value!r}) | collected: {list(collected.keys())}")
        await params.result_callback(
            {"ok": True, "field_id": field_id, "value": value, "say_back_as": spoken_value}
        )

    async def submit_form(params: FunctionCallParams) -> None:
        """Submit the completed intake form.

        Only call this after ALL required fields are filled and the patient
        has confirmed everything is correct.
        """
        missing = [f for f in REQUIRED_FIELDS if f not in collected]
        if missing:
            await params.result_callback({"ok": False, "missing_required": missing})
            return

        await params.llm.push_frame(
            RTVIUICommandFrame(
                command="click",
                payload=Click(target_id="submit-intake").model_dump(),
            ),
            FrameDirection.DOWNSTREAM,
        )

        await _post_intake(session_id, collected)
        logger.info(f"Form submitted: session={session_id} collected={collected}")
        await params.result_callback({"ok": True, "session_id": session_id})

    async def end_call(params: FunctionCallParams) -> None:
        """End the session. Only call after saying goodbye to the patient."""
        logger.info("end_call — pushing EndTaskFrame")
        await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
        await params.result_callback(
            {"ok": True}, properties=FunctionCallResultProperties(run_llm=False)
        )

    tool_functions = [fill_form_field, submit_form, end_call]
    tools = ToolsSchema(standard_tools=tool_functions)

    # ── System prompt ─────────────────────────────────────────────────────

    fields_list = "\n".join(f"  - {fid}: {desc}" for fid, desc in INTAKE_FIELDS.items())
    required_list = ", ".join(REQUIRED_FIELDS)

    system_instruction = f"""You are ClearPath, a medical intake assistant for Valley Medical Center.
Collect each intake form field from the patient by voice, one at a time.

FIELDS (use exact field_id when calling fill_form_field):
{fields_list}

REQUIRED fields: {required_list}

=== STRICT TURN RULES ===
Each of your turns must follow this exact pattern:
  STEP 1: If the patient just answered a question → call fill_form_field(field_id, value) for that answer.
  STEP 2: Speak ONE short sentence (the next question OR a brief confirmation + next question).
  STEP 3: STOP. Do not ask multiple questions. Do not fill fields you haven't asked about yet.

Never call fill_form_field for a field before asking the patient for it.
Never ask two questions in the same turn.
Never generate more than 2 sentences total per turn.

FIELD ORDER:
1. patient-name → 2. date-of-birth → 3. phone-number → 4. reason-for-visit →
5. medical-conditions → 6. current-medications → 7. medication-dosages →
8. allergies → 9. allergy-reactions → 10. insurance-provider → 11. member-id →
12. group-number → 13. emergency-name → 14. emergency-relationship → 15. emergency-phone

OPTIONAL fields (6,7,9,12): if patient says "none", "no", "skip" → call fill_form_field(field_id, "none") and move on.

LONG NUMBERS (member-id, group-number, phone numbers):
- These can be long. The patient may pause between groups of digits — that does NOT mean they are finished.
- After they give a number, READ IT BACK and ask "Did I get that right?" before moving to the next field.
- When you read a number back, say it using the "say_back_as" value from the tool result (digits spoken one at a time), not as a single large number.
- If they say it's wrong or give more digits, call fill_form_field again with the corrected/complete value.
- Only advance to the next field once they confirm the number is correct.

WHEN ALL REQUIRED FIELDS ARE FILLED:
→ Call submit_form.
→ Say "Your intake is submitted. See you soon!"
→ Call end_call.

VOICE STYLE:
- Short sentences only. No filler words. No "Great!", "Absolutely!", "Of course!".
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
            extra={
                "extra_body": {
                    "chat_template_kwargs": {"enable_thinking": enable_thinking}
                }
            },
        ),
    )

    tts = GradiumTTSService(
        api_key=os.environ["GRADIUM_API_KEY"],
        settings=GradiumTTSService.Settings(
            # Use `or` not a default arg — env var present but blank returns ""
            voice=os.getenv("GRADIUM_VOICE_ID") or "Eu9iL_CYe8N-Gkx_",
        ),
    )

    for fn in tool_functions:
        llm.register_direct_function(fn)

    # VAD tuned for medical intake: patients pause between digit groups when
    # reciting long member IDs / phone numbers. The default stop_secs=0.2 ends
    # the turn at the first pause, so half a number bleeds into the next field.
    # stop_secs=1.0 keeps the turn open through natural mid-number pauses.
    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(
            confidence=0.7,
            start_secs=0.2,
            stop_secs=1.0,
            min_volume=0.6,
        )
    )

    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=vad_analyzer,
            # No FilterIncompleteUserTurnStrategies — short answers like "none",
            # phone numbers, and single-word replies were being filtered out
        ),
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
        logger.info("Patient connected")
        context.add_message({
            "role": "user",
            "content": (
                "The patient has just opened the intake form in their browser. "
                "Greet them warmly as ClearPath, Valley Medical Center's intake assistant, "
                "and ask for their full legal name to get started."
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

    await run_bot(transport, **transport_overrides)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
