"""Role-aware local model inventory and Ollama residency status."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from atelier.config import settings


@dataclass(frozen=True)
class ModelRecord:
    role: str
    model_id: str
    quantization: str
    memory_estimate_gb: float
    context_tokens: int
    modality: str
    supports_tools: bool
    supports_json: bool
    configured: bool = True
    installed: bool = False
    resident: bool = False
    disk_size_gb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_ROLE_METADATA = {
    "worker": ("Q6_K", 3.0, 32768, "text", True, True),
    "brain": ("Q4-class", 10.0, 40960, "text", True, True),
    "coder": ("Q4-class", 6.0, 40960, "text", True, True),
    "heavy": ("Q4-class", 20.0, 262144, "text,image", True, True),
    "router": ("Q4-class", 3.0, 40960, "text", True, True),
    "expert": ("unknown", 0.0, 0, "unknown", False, False),
}


class ModelLifecycle:
    """Build model records from config plus local Ollama state."""

    def __init__(self, ollama_url: str | None = None) -> None:
        self.ollama_url = ollama_url or settings.ollama_url

    def _ollama_state(self) -> tuple[dict[str, dict[str, Any]], set[str]]:
        try:
            import ollama

            client = ollama.Client(host=self.ollama_url)
            listed = client.list().get("models", [])
            resident = client.ps().get("models", [])
        except Exception:  # noqa: BLE001 - status should remain inspectable
            return {}, set()
        available = {
            str(row.get("model", row.get("name", ""))): row
            for row in listed
            if row.get("model", row.get("name"))
        }
        resident_names = {
            str(row.get("name", row.get("model", "")))
            for row in resident
            if row.get("name", row.get("model"))
        }
        return available, resident_names

    def list(self) -> list[ModelRecord]:
        available, resident = self._ollama_state()
        configured = {
            "worker": settings.worker_model,
            "brain": settings.brain_model,
            "coder": settings.coder_model,
            "heavy": settings.heavy_model,
            "router": settings.router_model,
            "expert": settings.expert_model,
        }
        records: list[ModelRecord] = []
        for role, model_id in configured.items():
            metadata = _ROLE_METADATA[role]
            row = available.get(model_id, {}) if model_id else {}
            size = row.get("size")
            records.append(ModelRecord(
                role=role, model_id=model_id, quantization=metadata[0],
                memory_estimate_gb=metadata[1], context_tokens=metadata[2],
                modality=metadata[3], supports_tools=metadata[4],
                supports_json=metadata[5], configured=bool(model_id),
                installed=bool(model_id and model_id in available),
                resident=bool(model_id and model_id in resident),
                disk_size_gb=round(float(size) / (1024**3), 2) if isinstance(size, (int, float)) else None,
            ))
        return records

    def status(self) -> dict[str, Any]:
        records = self.list()
        return {
            "ollama_url": self.ollama_url,
            "models": [record.to_dict() for record in records],
            "resident_count": sum(record.resident for record in records),
            "installed_count": sum(record.installed for record in records),
        }

    def bench(self, model: str, *, max_steps: int = 14) -> dict[str, Any]:
        from eval.coding_benchmark import run, save

        report = run([model], max_steps=max_steps)
        report["lifecycle_role"] = next(
            (record.role for record in self.list() if record.model_id == model),
            "unassigned",
        )
        report["report_path"] = str(save(report))
        return report
