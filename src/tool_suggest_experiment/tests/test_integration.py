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


def test_baseline_csv_output():
    from tool_suggest_experiment.experiment_runner import run_baseline

    api_key = os.environ["OPENAI_API_KEY"]

    with tempfile.TemporaryDirectory() as tmpdir:
        output = os.path.join(tmpdir, "test_baseline.csv")
        run_baseline(["text editor"], api_key, output, num_runs=1)

        assert Path(output).exists()
        import csv
        with open(output, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) >= 2
        assert len(rows[0]) == len(rows[1])
