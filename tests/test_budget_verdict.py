from animated_infographics.evals.budget_verdict import budget_verdict


def test_budget_verdict_all_under():
    spans = {"new": 200.0, "render": 180.0, "total": 380.0}
    bars = {"new": 390.0, "render": 210.0, "total": 600.0}
    assert budget_verdict(spans, bars) == 0


def test_budget_verdict_one_span_over():
    spans = {"new": 200.0, "render": 210.01, "total": 410.01}
    bars = {"new": 390.0, "render": 210.0, "total": 600.0}
    assert budget_verdict(spans, bars) == 3


def test_budget_verdict_exactly_at_bar():
    spans = {"new": 390.0, "render": 210.0, "total": 600.0}
    bars = {"new": 390.0, "render": 210.0, "total": 600.0}
    assert budget_verdict(spans, bars) == 0


def test_budget_verdict_october_9_long_literal():
    # Long literal judged on total only (bar <= 170 s/min)
    # October 9 measured numbers: render 80.47 s/min, total 138.90 s/min
    spans = {"total": 138.90}
    bars = {"total": 170.0}
    assert budget_verdict(spans, bars) == 0


def test_budget_verdict_long_total_over():
    spans = {"total": 170.01}
    bars = {"total": 170.0}
    assert budget_verdict(spans, bars) == 3
