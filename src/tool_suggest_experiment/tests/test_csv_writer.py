import csv
import tempfile
from pathlib import Path

from tool_suggest_experiment.csv_writer import write_results, _build_headers
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

        assert rows[0] == _build_headers(3)
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


def test_headers_dynamic():
    h1 = _build_headers(1)
    assert h1[0] == "task"
    assert "run1_score" in h1
    assert "run2_score" not in h1
    assert "avg_score" in h1
    assert len(h1) == 9

    h3 = _build_headers(3)
    assert "run1_score" in h3
    assert "run3_score" in h3
    assert len(h3) == 17


def test_write_single_run():
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.csv"
        runs = [RunMetrics(total_tokens=100, steps=5, duration_sec=10.0, judge_scores=[8.0])]
        write_results(output, [("task1", runs)])

        with open(output, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        assert rows[0] == _build_headers(1)
        assert len(rows[1]) == len(rows[0])
