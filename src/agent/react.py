"""ReAct loop: thought, tool, observation, repeat, then a grounded answer."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from agent.planner import decide
from agent.render import render
from agent.tools import call_tool
from grocery_shock.paths import MELBOURNE


def run_agent(question: str, *, max_steps: int = 6) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    payloads: dict[str, dict] = {}
    called: set[str] = set()
    started = datetime.now(ZoneInfo(MELBOURNE)).isoformat(timespec="seconds")

    for _ in range(max_steps):
        decision = decide(question, called)
        steps.append({"kind": "thought", "text": decision.thought})
        if decision.kind == "final":
            break
        arguments = decision.arguments or {}
        steps.append({"kind": "action", "tool": decision.tool, "arguments": arguments})
        try:
            payload = call_tool(decision.tool, arguments)
            observation = {"ok": True, "payload": payload}
            payloads[decision.tool] = payload
        except Exception as exc:
            observation = {"ok": False, "error": str(exc)}
        called.add(decision.tool)
        steps.append({"kind": "observation", "tool": decision.tool, **observation})
    else:
        steps.append({"kind": "thought", "text": "Stopping after the step limit."})

    rendered = render(payloads)
    steps.append({"kind": "final", "text": rendered["answer"], "citations": rendered["citations"]})
    return {
        "question": question,
        "started_at": started,
        "timezone": MELBOURNE,
        "steps": steps,
        "answer": rendered["answer"],
        "citations": rendered["citations"],
        "tools_used": [step["tool"] for step in steps if step["kind"] == "action"],
    }
