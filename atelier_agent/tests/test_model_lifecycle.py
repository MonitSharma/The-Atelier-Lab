from models.lifecycle import ModelLifecycle


def test_lifecycle_combines_configured_roles_with_local_state(monkeypatch) -> None:
    lifecycle = ModelLifecycle()
    monkeypatch.setattr(
        lifecycle,
        "_ollama_state",
        lambda: ({"qwen3:8b": {"size": 5 * 1024**3}}, {"qwen3:8b"}),
    )
    records = {record.role: record for record in lifecycle.list()}
    assert records["coder"].installed
    assert records["coder"].resident
    assert records["coder"].disk_size_gb == 5.0
    assert records["expert"].configured is False
