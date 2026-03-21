from tool_suggest_experiment.metrics import RunMetrics


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
