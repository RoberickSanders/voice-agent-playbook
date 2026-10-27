#!/usr/bin/env python3
"""Place ONE outbound call with an optional per-call prompt override.
The standing prompt is never modified; the override applies to this call only.
Requires --confirm so a call can't be placed by accident.
   python scripts/outbound_call.py --to 555-0100 --name "Jane Doe" --prompt-file prompts/pass_message.md --confirm"""
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _el import call
ROOT = Path(__file__).resolve().parents[1]
SPOKEN_ONLY = (ROOT / "config/standing_prompt.md").read_text().split("# Personality")[0]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="E.164 number")
    ap.add_argument("--name", default="")
    ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    agent = {"first_message": f"Hi {a.name}?" if a.name else "", "language": "en"}
    if a.prompt_file:
        task = a.prompt_file.read_text()
        if "# Spoken output only" not in task:   # every per-call prompt must start with the no-leak block
            task = SPOKEN_ONLY + "\n" + task
        agent["prompt"] = {"prompt": task, "llm": "gemini-2.0-flash"}
    body = {"agent_id": os.environ.get("ELEVENLABS_AGENT_ID", "<agent_id>"),
            "agent_phone_number_id": os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", "<phone_number_id>"),
            "to_number": a.to,
            "conversation_initiation_client_data": {"dynamic_variables": {"name": a.name},
                                                    "conversation_config_override": {"agent": agent}}}
    if not a.confirm:
        print("DRY RUN (add --confirm to dial):"); print(json.dumps(body, indent=2)[:2000]); sys.exit(0)
    r = call("POST", "/v1/convai/twilio/outbound-call", body)
    print(json.dumps({k: r.get(k) for k in ("conversation_id", "callSid", "success")}))
