#!/usr/bin/env python3
"""Run scripted caller scenarios against the agent with ElevenLabs' simulate-conversation API
(no phone call, no cost per dial) and leak-check each transcript.
   python scripts/simulate.py config/scenarios.json"""
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from _el import call; from leak_check import check

if __name__ == "__main__":
    agent = os.environ["ELEVENLABS_AGENT_ID"]
    scen = json.loads(Path(sys.argv[1]).read_text())
    out = []
    for s in scen:
        r = call("POST", f"/v1/convai/agents/{agent}/simulate-conversation",
                 {"simulation_specification": {"simulated_user_config": {"prompt": {"prompt": s["caller"]}}}})
        conv = r.get("simulated_conversation", [])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"transcript": conv}, f)
        res = check(Path(f.name)); res["scenario"] = s["id"]; out.append(res)
        print(f"{s['id']:<24} {'PASS' if res['pass'] else 'FAIL'} {len(res['issues'])} issue(s)")
    Path("simulation-results.json").write_text(json.dumps(out, indent=2))
