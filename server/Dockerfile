FROM dailyco/pipecat-base:latest

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Uncomment if you wish to print a summary of the features available in the base image
# ENV PCC_LOG_FEATURES_SUMMARY=true

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy the application code.
# Pipecat Cloud runs bot.py as the entry point, so the ClearPath intake bot is
# copied in as bot.py along with all of its helper modules.
COPY ./bot-intake.py bot.py
COPY ./intake_fields.py intake_fields.py
COPY ./nemotron_llm.py nemotron_llm.py
COPY ./nvidia_stt.py nvidia_stt.py
COPY ./number_utils.py number_utils.py