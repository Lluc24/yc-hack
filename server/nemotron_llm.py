#
# Copyright (c) 2024–2026, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""vLLM OpenAI-compatible LLM service with:
  - TTFB timed to first NON-THINKING token
  - Thinking-token stripping at the chunk level (before Pipecat text aggregation)
  - ✓ turn-marker stripping

Strips <think>...</think> blocks and bare ✓ markers from streaming delta.content
before they reach Pipecat's text pipeline, so the StripThinkingProcessor in
bot-intake.py is a belt-and-suspenders backup rather than primary defence.
"""

import re

from loguru import logger

from pipecat.services.openai.llm import OpenAILLMService

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


class VLLMOpenAILLMService(OpenAILLMService):
    """OpenAI-compatible vLLM service with thinking-token stripping and accurate TTFB."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ttft_armed = False
        self._in_thinking = False  # state across chunks for this turn

    async def get_chat_completions(self, context):
        """Wrap the chunk stream to:
        1. Arm TTFB on first real content/tool delta
        2. Strip <think>...</think> content and ✓ markers from delta.content
        """
        self._ttft_armed = False
        self._in_thinking = False
        stream = await super().get_chat_completions(context)

        async def _cleaned_stream():
            try:
                async for chunk in stream:
                    choices = getattr(chunk, "choices", None)
                    delta = getattr(choices[0], "delta", None) if choices else None
                    content = getattr(delta, "content", None) if delta else None

                    if content is not None:
                        logger.debug(f"[NEMOTRON RAW] {repr(content)}")
                        clean = self._strip_thinking(content)
                        logger.debug(f"[NEMOTRON CLEAN] {repr(clean)}")

                        if clean != content:
                            delta.content = clean  # delta is mutable

                        # TTFB: arm only on first real (non-empty, non-thought) token
                        if not self._ttft_armed and clean:
                            self._ttft_armed = True

                        if not clean:
                            # Nothing to speak — skip yielding this chunk
                            continue
                    else:
                        # Tool calls or role-only chunks: arm TTFB and pass through
                        if not self._ttft_armed and delta is not None:
                            if getattr(delta, "tool_calls", None):
                                self._ttft_armed = True

                    yield chunk

            finally:
                if hasattr(stream, "close"):
                    await stream.close()
                elif hasattr(stream, "aclose"):
                    await stream.aclose()

        return _cleaned_stream()

    def _strip_thinking(self, text: str) -> str:
        """Strip thinking content from a single chunk, maintaining cross-chunk state."""
        result: list[str] = []
        i = 0
        while i < len(text):
            if self._in_thinking:
                end = text.find(_THINK_CLOSE, i)
                if end != -1:
                    self._in_thinking = False
                    i = end + len(_THINK_CLOSE)
                else:
                    # Entire chunk is thinking content — discard
                    break
            else:
                start = text.find(_THINK_OPEN, i)
                if start != -1:
                    result.append(text[i:start])
                    self._in_thinking = True
                    i = start + len(_THINK_OPEN)
                else:
                    result.append(text[i:])
                    break

        cleaned = "".join(result)
        # Strip ✓ turn-completion marker that Nemotron sometimes emits
        cleaned = cleaned.replace("✓", "")
        return cleaned

    async def stop_ttfb_metrics(self, *, end_time: float | None = None):
        """Only record TTFB once a real (non-thinking) token has streamed."""
        if self._ttft_armed:
            await super().stop_ttfb_metrics(end_time=end_time)
