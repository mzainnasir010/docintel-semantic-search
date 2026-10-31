"""Fast end-to-end test for the configurable chunk experiment harness."""

import csv

import numpy as np

from eval.chunking_experiments import ExperimentConfig, run_experiments


class TinyEmbedder:
    model_name = "tiny-model"

    def embed_documents(self, texts):
        return np.asarray(
            [
                [text.lower().count("alpha") + 1, text.lower().count("beta") + 1, 1]
                for text in texts
            ],
            dtype=np.float32,
        )


def test_experiment_harness_runs_tiny_corpus_and_writes_artifacts(tmp_path) -> None:
    corpus_file = tmp_path / "python_asyncio.txt"
    corpus_file.write_text("alpha concept is stored here.", encoding="utf-8")
    questions = [
        {
            "id": "tiny-q1",
            "question": "Where is the alpha concept documented?",
            "expected_doc_name": "python_asyncio.txt",
            "expected_pages": [1],
            "expected_answer": "In the alpha concept text.",
            "type": "direct",
        }
    ]
    csv_path = tmp_path / "chunking.csv"
    report_path = tmp_path / "CHUNKING_EXPERIMENTS.md"

    rows = run_experiments(
        configurations=[ExperimentConfig("recursive", 40, 0)],
        corpus_paths=[corpus_file],
        questions=questions,
        output_csv=csv_path,
        report_path=report_path,
        embedder=TinyEmbedder(),
    )

    assert len(rows) == 1
    assert rows[0]["hit_at_5"] == 1.0
    assert rows[0]["mrr"] == 1.0
    with csv_path.open(encoding="utf-8", newline="") as source:
        persisted = list(csv.DictReader(source))
    assert len(persisted) == 1
    assert persisted[0]["strategy"] == "recursive"
    assert "Selected configuration" in report_path.read_text(encoding="utf-8")
