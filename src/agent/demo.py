"""CLI: python -m agent.demo \"Which food categories hurt most?\""""

from __future__ import annotations

import argparse
import json
import sys

from agent.questions import DEMO_QUESTIONS
from agent.react import run_agent
from grocery_shock.paths import traces_dir


def slug(question: str) -> str:
    keep = [char.lower() if char.isalnum() else "-" for char in question]
    return "".join(keep).strip("-")[:80]


def write_trace(trace: dict) -> None:
    folder = traces_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{slug(trace['question'])}.json").write_text(json.dumps(trace, indent=2) + "\n")


def run_questions(questions: list[str]) -> list[dict]:
    traces = []
    for question in questions:
        trace = run_agent(question)
        write_trace(trace)
        traces.append(trace)
    folder = traces_dir()
    (folder / "demo_bundle.json").write_text(json.dumps(traces, indent=2) + "\n")
    return traces


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ask the grocery briefing agent.")
    parser.add_argument("question", nargs="?")
    parser.add_argument("--all", action="store_true", help="Run the baked stakeholder questions.")
    args = parser.parse_args(argv)
    if args.all:
        traces = run_questions(DEMO_QUESTIONS)
        for trace in traces:
            print(f"\nQ: {trace['question']}\nA: {trace['answer']}")
        return
    if not args.question:
        parser.error("Pass a question or --all")
    trace = run_agent(args.question)
    write_trace(trace)
    print(trace["answer"])


if __name__ == "__main__":
    main(sys.argv[1:])
