from tool_suggest_experiment.metrics import RunMetrics, average_metrics


def test_run_metrics_defaults():
    m = RunMetrics()
    assert m.total_tokens == 0
    assert m.steps == 0
    assert m.duration_sec == 0.0
    assert m.success is False
    assert m.avg_judge_score == 0.0


def test_avg_judge_score():
    m = RunMetrics(judge_scores=[8.0, 7.0, 9.0])
    assert m.avg_judge_score == 8.0


def test_average_metrics():
    runs = [
        RunMetrics(total_tokens=100, steps=5, duration_sec=10.0, judge_scores=[8.0]),
        RunMetrics(total_tokens=200, steps=10, duration_sec=20.0, judge_scores=[6.0]),
    ]
    avg = average_metrics(runs)
    assert avg["avg_tokens"] == 150.0
    assert avg["avg_steps"] == 7.5
    assert avg["avg_time"] == 15.0
    assert avg["avg_score"] == 7.0


def test_average_metrics_empty():
    assert average_metrics([]) == {}
