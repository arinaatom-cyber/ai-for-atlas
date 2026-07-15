from atlas_agent.discovery.benchmark import evaluate_literature_benchmark, evaluate_project_benchmark


def test_literature_benchmark_accuracy():
    m = evaluate_literature_benchmark()
    assert m["n"] >= 4
    assert m["accuracy"] >= 0.75


def test_project_benchmark_accuracy():
    m = evaluate_project_benchmark()
    assert m["n"] >= 3
    assert m["accuracy"] >= 0.66
