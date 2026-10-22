#!/usr/bin/env python3
"""QA a call transcript for the failure modes found in real test calls.
Input: a conversation JSON from GET /v1/convai/conversations/{id}, or a plain-text transcript
with lines like 'agent: ...' / 'user: ...'.
   python scripts/leak_check.py examples/sample_transcript.txt"""
import json, re, sys
from pathlib import Path

CHECKS = {
    "tag_leak": re.compile(r"\[[a-z_ ]+\]", re.I),
    "reasoning_leak": re.compile(r"\b(the user (said|stated|is)|according to (the )?(script|instructions)|i should|i need to|let me think|my instructions)\b", re.I),
    "label_leak": re.compile(r"\b(end_call|skip_turn|voicemail_detection|system prompt|tool call)\b", re.I),
    "recap_after_interrupt": re.compile(r"\b(as i (was saying|mentioned)|like i was saying|i understand you said)\b", re.I),
    "filler_on_silence": re.compile(r"^\s*(oh,? )?(gotcha|okay|oh)[.!]?\s*$", re.I),
}

def turns(path: Path):
    t = path.read_text()
    if t.lstrip().startswith("{"):
        for x in json.loads(t).get("transcript", []):
            yield x.get("role"), x.get("message") or ""
    else:
        for line in t.splitlines():
            m = re.match(r"\s*(agent|user)\s*:\s*(.*)", line, re.I)
            if m: yield m.group(1).lower(), m.group(2)

def check(path: Path) -> dict:
    hits = []
    agent_turns = 0
    for i, (role, msg) in enumerate(turns(path)):
        if role != "agent": continue
        agent_turns += 1
        for name, rx in CHECKS.items():
            if rx.search(msg): hits.append({"turn": i, "check": name, "text": msg[:120]})
    return {"file": path.name, "agent_turns": agent_turns, "issues": hits, "pass": not hits}

if __name__ == "__main__":
    res = [check(Path(p)) for p in sys.argv[1:]]
    print(json.dumps(res, indent=2)); sys.exit(0 if all(r["pass"] for r in res) else 1)
