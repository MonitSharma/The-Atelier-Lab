from eval.coding_benchmark import _local_path, _trace_metrics
from atelier.config import settings
from models.registry import specs_from_settings


def test_benchmark_normalizes_workspace_paths() -> None:
    assert _local_path(".coding_benchmark_workspace/task/config.py", "task") == "config.py"
    assert _local_path("./test_config.py", "task") == "test_config.py"


def test_benchmark_counts_reads_and_edit_failures() -> None:
    trace = [
        {"decision": {"tool": "read_file", "arguments": {"path": "task/source.py"}},
         "observation": {"status": "success"}},
        {"decision": {"tool": "read_file", "arguments": {"path": "task/other.py"}},
         "observation": {"status": "success"}},
        {"decision": {"tool": "edit_file", "arguments": {"path": "task/source.py"}},
         "observation": {"status": "error"}},
    ]
    metrics = _trace_metrics(trace, [], {"source.py"}, "task")
    assert metrics["reads"] == 2
    assert metrics["unnecessary_reads"] == 1
    assert metrics["invalid_edits"] == 1
    assert metrics["tool_errors"] == 1


def test_coder_is_a_configured_model_role() -> None:
    specs = specs_from_settings(settings)
    assert "coder" in specs
    assert specs["coder"].model_id == "qwen3:8b"
