"""
Integration tests for the experiment pipeline.
These tests require LLM API access and take ~2 minutes each.
Run with: uv run python -m pytest src/tool_suggest_experiment/tests/test_integration.py -v -s
"""
import os
import tempfile
import pytest
from pathlib import Path


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


def test_baseline_single_task():
    from tool_suggest_experiment.experiment_runner import run_single_task, run_judge_single

    api_key = os.environ["OPENAI_API_KEY"]

    metrics, lm = run_single_task("text editor", api_key)

    assert metrics.total_tokens > 0
    assert metrics.steps > 0
    assert metrics.duration_sec > 0

    if metrics.success:
        score = run_judge_single(str(lm.run_dir), api_key)
        assert 0 <= score <= 10


def test_full_experiment():
    from tool_suggest_experiment.experiment_runner import run_full_experiment

    api_key = os.environ["OPENAI_API_KEY"]

    with tempfile.TemporaryDirectory() as tmpdir:
        baseline_csv = os.path.join(tmpdir, "baseline.csv")
        toolsuggest_csv = os.path.join(tmpdir, "toolsuggest.csv")
        run_full_experiment(
            ["calculator"], api_key,
            baseline_csv=baseline_csv,
            toolsuggest_csv=toolsuggest_csv,
            num_runs=1,
        )

        assert Path(baseline_csv).exists()
        assert Path(toolsuggest_csv).exists()

        import csv
        for csv_path in [baseline_csv, toolsuggest_csv]:
            with open(csv_path, "r") as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert len(rows) >= 2
            assert len(rows[0]) == len(rows[1])
