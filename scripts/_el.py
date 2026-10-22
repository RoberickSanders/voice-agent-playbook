"""Tiny ElevenLabs Conversational AI client. Key from ELEVENLABS_API_KEY (never printed)."""
import json, os, urllib.request

BASE = "https://api.elevenlabs.io"

def call(method: str, path: str, body: dict | None = None) -> dict:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("Set ELEVENLABS_API_KEY in your environment (see .env.example).")
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": key, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)
