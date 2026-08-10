"""Explicit, read-only Quantinuum device discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..policy import HELIOS_1E_EMULATOR, HardwarePolicyError


class QuantinuumDependencyError(ImportError):
    """Raised when read-only Nexus discovery cannot import qnexus."""


@dataclass(frozen=True)
class DeviceRecord:
    device_name: str
    backend_name: str
    nexus_hosted: bool | None
    system_type: str | None
    n_qubits: int | None


def discover_devices() -> tuple[DeviceRecord, ...]:
    """Query the authenticated Nexus catalogue without submitting a job."""

    try:
        import qnexus as qnx
    except ImportError as exc:  # pragma: no cover - optional provider stack
        raise QuantinuumDependencyError("install the qatelier-quantinuum extra") from exc
    records: list[DeviceRecord] = []
    for device in qnx.devices.get_all():
        info: Any = getattr(device, "backend_info", None)
        misc = getattr(info, "misc", None) or {}
        records.append(
            DeviceRecord(
                device_name=str(device.device_name),
                backend_name=str(device.backend_name),
                nexus_hosted=getattr(device, "nexus_hosted", None),
                system_type=misc.get("system_type") if isinstance(misc, dict) else None,
                n_qubits=(
                    getattr(info, "n_qubits", None)
                    or (misc.get("n_qubits_sv") if isinstance(misc, dict) else None)
                    or (misc.get("n_qubits_stb") if isinstance(misc, dict) else None)
                ),
            )
        )
    return tuple(records)


def require_helios_1e_identifier(records: tuple[DeviceRecord, ...] | None = None) -> DeviceRecord:
    """Return the exact exposed emulator identifier or fail closed."""

    records = discover_devices() if records is None else records
    matches = [record for record in records if record.device_name == HELIOS_1E_EMULATOR]
    if len(matches) != 1:
        raise HardwarePolicyError(
            f"expected exactly one configured {HELIOS_1E_EMULATOR} emulator identifier; found {len(matches)}"
        )
    record = matches[0]
    if record.backend_name.lower() != "quantinuum":
        raise HardwarePolicyError(
            f"{HELIOS_1E_EMULATOR} resolved to unexpected provider {record.backend_name!r}"
        )
    return record


__all__ = ["DeviceRecord", "QuantinuumDependencyError", "discover_devices", "require_helios_1e_identifier"]
