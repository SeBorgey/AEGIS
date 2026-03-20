import csv
import tempfile
from pathlib import Path

from tool_suggest_experiment.csv_writer import write_results, HEADERS
from tool_suggest_experiment.metrics import RunMetrics


def test_write_single_task():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.csv"
        runs = [
            RunMetrics(task="test", total_tokens=100, steps=5, duration_sec=10.0, judge_scores=[8.0, 7.0, 9.0]),
            RunMetrics(task="test", total_tokens=200, steps=10, duration_sec=20.0, judge_scores=[6.0, 5.0, 7.0]),
            RunMetrics(task="test", total_tokens=150, steps=7, duration_sec=15.0, judge_scores=[7.0, 8.0, 6.0]),
        ]
        write_results(output, [("test task", runs)])

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == HEADERS
        assert len(rows) == 2
        assert rows[1][0] == "test task"


def test_write_multiple_tasks():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.csv"
        runs1 = [RunMetrics(judge_scores=[8.0])] * 3
        runs2 = [RunMetrics(judge_scores=[6.0])] * 3
        write_results(output, [("task1", runs1), ("task2", runs2)])

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[1][0] == "task1"
        assert rows[2][0] == "task2"


def test_headers_format():
    assert HEADERS[0] == "task"
    assert "avg_score" in HEADERS
    assert "avg_tokens" in HEADERS
    assert "avg_steps" in HEADERS
    assert "avg_time" in HEADERS
    assert len(HEADERS) == 17
