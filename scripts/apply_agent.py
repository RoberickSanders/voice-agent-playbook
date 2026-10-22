#!/usr/bin/env python3
"""Create or update the agent from config/agent_config.example.json + config/standing_prompt.md.
   python scripts/apply_agent.py            # dry run: prints the payload
   python scripts/apply_agent.py --apply    # creates (no ELEVENLABS_AGENT_ID) or PATCHes the agent"""
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _el import call
ROOT = Path(__file__).resolve().parents[1]

def payload(cfg_path: Path) -> dict:
    cfg = json.loads(cfg_path.read_text()); cfg.pop("_notes", None)
    pr = cfg["conversation_config"]["agent"]["prompt"]
    if pr["prompt"].startswith("@"):
        pr["prompt"] = (ROOT / pr["prompt"][1:]).read_text()
    return cfg

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--config", type=Path, default=ROOT / "config/agent_config.example.json")
    ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    body = payload(a.config)
    if not a.apply:
        print(json.dumps(body, indent=2)[:3000]); sys.exit(0)
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID")
    r = call("PATCH", f"/v1/convai/agents/{agent_id}", body) if agent_id else call("POST", "/v1/convai/agents/create", body)
    print(json.dumps({"agent_id": r.get("agent_id", agent_id)}))
