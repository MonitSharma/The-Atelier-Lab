from router_policy import model_route


def test_easy_single_line_routes_to_worker():
    assert model_route("easy", "single_line") == "worker"


def test_medium_multiline_routes_to_brain():
    assert model_route("medium", "multi_line") == "brain"


def test_combined_tasks_route_to_brain():
    assert model_route("easy", "single_line", combined=True) == "brain"
