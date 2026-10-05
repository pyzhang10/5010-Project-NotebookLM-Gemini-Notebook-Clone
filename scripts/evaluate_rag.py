"""Run both retrieval approaches and export evidence for manual answer scoring.

Usage after adding sources through the application:
  python scripts/evaluate_rag.py NOTEBOOK_UUID docs/evaluation_questions.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval import VectorIndex
from storage import LocalStorage


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/evaluate_rag.py NOTEBOOK_UUID QUESTIONS_JSON")
    notebook_id = sys.argv[1]
    questions = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    index = VectorIndex(LocalStorage())
    rows = []
    for question in questions:
        for method in ("Vector Search", "Hybrid Search"):
            results, elapsed = index.search(notebook_id, question, method)
            rows.append({
                "question": question,
                "method": method,
                "retrieved_chunk_ids": " | ".join(item.chunk_id for item in results),
                "retrieved_sources": " | ".join(
                    f"{item.metadata['source_name']} ({item.metadata['location']})"
                    for item in results
                ),
                "retrieval_time_seconds": f"{elapsed:.4f}",
                "answer_quality_1_to_5": "",
                "citation_correct_yes_no": "",
                "notes": "",
            })
    output = ROOT / "rag_evaluation_results.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} comparison rows to {output}")


if __name__ == "__main__":
    main()

