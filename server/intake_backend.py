"""ClearPath intake REST API.

Stores completed intake records (file-backed JSON so they survive restarts)
and serves them to the results dashboard.

Run standalone:
    uvicorn intake_backend:app --port 8000 --reload

Endpoints:
    POST /api/intake            save a completed intake
    GET  /api/intakes           list all intakes (newest first)
    GET  /api/intakes/{id}      fetch one intake
    DELETE /api/intakes         clear all (handy between demos)
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

app = FastAPI(title="ClearPath Intake API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon — lock down post-event
    allow_methods=["*"],
    allow_headers=["*"],
)

# File-backed store so records survive an API restart during the demo.
_STORE_PATH = Path(__file__).parent / "intakes.json"


def _load() -> dict[str, dict]:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text())
        except Exception as exc:
            logger.warning(f"Could not read {_STORE_PATH}: {exc}")
    return {}


def _save(store: dict[str, dict]) -> None:
    _STORE_PATH.write_text(json.dumps(store, indent=2))


_intakes: dict[str, dict] = _load()


class IntakeRecord(BaseModel):
    session_id: str
    fields: dict[str, str]
    timestamp: str = ""
    source: str = "web"  # "web" or "phone"


@app.post("/api/intake")
async def save_intake(record: IntakeRecord):
    if not record.timestamp:
        record.timestamp = datetime.utcnow().isoformat()
    _intakes[record.session_id] = record.model_dump()
    _save(_intakes)
    logger.info(f"Saved intake {record.session_id} ({record.source}) — {len(record.fields)} fields")
    return {"ok": True, "session_id": record.session_id}


@app.get("/api/intakes")
async def list_intakes():
    # Newest first
    records = sorted(_intakes.values(), key=lambda r: r.get("timestamp", ""), reverse=True)
    return {"intakes": records}


@app.get("/api/intakes/{session_id}")
async def get_intake(session_id: str):
    record = _intakes.get(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@app.delete("/api/intakes")
async def clear_intakes():
    count = len(_intakes)
    _intakes.clear()
    _save(_intakes)
    logger.info(f"Cleared {count} intake records")
    return {"ok": True, "cleared": count}
