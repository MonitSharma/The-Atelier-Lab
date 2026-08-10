"""Configuration loading and execution-readiness checks for QAtelier.

The committed QAtelier configuration is the locked current-phase research
protocol. It records the frozen encoder/artifact identifiers and the explicit
no-candidate hardware decision. Structural validation remains separate from
execution readiness so future protocol changes cannot silently become runnable.

The loader is intentionally local-only: it never reads provider credentials,
contacts a backend, or imports a quantum SDK.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


class ConfigurationError(ValueError):
    """Base class for invalid or incomplete QAtelier configuration."""


class ConfigurationDependencyError(ConfigurationError):
    """Raised when an optional parser/validator dependency is unavailable."""


class UnresolvedScientificPlaceholderError(ConfigurationError):
    """Raised when execution is requested with unresolved protocol fields."""

    def __init__(self, issues: Iterable["PlaceholderIssue"]):
        self.issues = tuple(issues)
        details = "; ".join(f"{issue.path}: {issue.value!r}" for issue in self.issues)
        super().__init__(
            "execution blocked: unresolved scientific placeholders remain: " + details
        )


@dataclass(frozen=True)
class PlaceholderIssue:
    """One unresolved value and its deterministic JSON-style document path."""

    path: str
    value: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "value": self.value, "reason": self.reason}


@dataclass(frozen=True)
class ConfigValidationReport:
    """Result of structural and placeholder validation."""

    path: Path
    schema_path: Path
    placeholder_issues: tuple[PlaceholderIssue, ...] = ()
    schema_errors: tuple[str, ...] = ()

    @property
    def structurally_valid(self) -> bool:
        return not self.schema_errors

    @property
    def execution_ready(self) -> bool:
        return self.structurally_valid and not self.placeholder_issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_path": str(self.path),
            "schema_path": str(self.schema_path),
            "structurally_valid": self.structurally_valid,
            "execution_ready": self.execution_ready,
            "placeholder_issues": [issue.to_dict() for issue in self.placeholder_issues],
            "schema_errors": list(self.schema_errors),
        }


_PLACEHOLDER_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?:record|fill|set|define|choose|specify)_", re.IGNORECASE), "record-before-run marker"),
    (re.compile(r"(?:_before_run|_before_execution)$", re.IGNORECASE), "before-run marker"),
    (re.compile(r"(?:manifest_and_digest|record_parameters|recorded_separately)", re.IGNORECASE), "incomplete artifact/seed marker"),
    (re.compile(r"^unresolved$", re.IGNORECASE), "unresolved lock marker"),
    (re.compile(r"\b(?:placeholder|change_me|replace_me|to_be_decided|tbd|todo|fixme)\b", re.IGNORECASE), "placeholder marker"),
)


def default_config_path() -> Path:
    """Return the committed protocol configuration path."""

    return Path(__file__).with_name("config.yaml")


def default_config_schema_path() -> Path:
    """Return the QAtelier configuration schema shipped with this package."""

    return Path(__file__).with_name("schemas") / "config.schema.json"


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a mapping from YAML using the safe, local parser."""

    config_path = Path(path)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ConfigurationDependencyError(
            "QAtelier config validation requires PyYAML; install the QAtelier "
            "infrastructure dependencies before using --config."
        ) from exc

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
    except OSError as exc:
        raise ConfigurationError(f"could not read config {config_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"could not parse config {config_path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ConfigurationError(f"config {config_path} must contain a top-level mapping")
    return document


def _path_for(parent: str, key: object) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]"
    return f"{parent}.{key}" if parent != "$" else f"$.{key}"


def _placeholder_reason(value: str) -> str | None:
    for pattern, reason in _PLACEHOLDER_PATTERNS:
        if pattern.search(value.strip()):
            return reason
    return None


def find_unresolved_placeholders(document: Any) -> tuple[PlaceholderIssue, ...]:
    """Find explicit unresolved scientific markers in a nested document.

    The walk is deterministic and reports every string occurrence.  Ordinary
    protocol language such as ``training_split_only`` is not treated as a
    placeholder; only explicit marker forms are blocked.
    """

    issues: list[PlaceholderIssue] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key in sorted(value, key=lambda item: str(item)):
                walk(value[key], _path_for(path, key))
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                walk(item, _path_for(path, index))
        elif value is None:
            issues.append(
                PlaceholderIssue(path=path, value="<null>", reason="unresolved null value")
            )
        elif isinstance(value, str):
            reason = _placeholder_reason(value)
            if reason is not None:
                issues.append(PlaceholderIssue(path=path, value=value, reason=reason))

    walk(document, "$")
    return tuple(issues)


def _schema_errors(document: Mapping[str, Any], schema_path: Path) -> tuple[str, ...]:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ConfigurationDependencyError(
            "QAtelier schema validation requires jsonschema; install the QAtelier "
            "infrastructure dependencies before validating a config."
        ) from exc

    try:
        with schema_path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"could not read schema {schema_path}: {exc}") from exc

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    return tuple(
        f"$.{'.'.join(str(part) for part in error.path)}: {error.message}"
        if error.path
        else f"$: {error.message}"
        for error in errors
    )


def validate_config(
    path: str | Path = default_config_path(),
    *,
    schema_path: str | Path = default_config_schema_path(),
) -> ConfigValidationReport:
    """Validate config structure and report unresolved values without executing."""

    config_path = Path(path)
    resolved_schema_path = Path(schema_path)
    document = load_yaml(config_path)
    return ConfigValidationReport(
        path=config_path,
        schema_path=resolved_schema_path,
        placeholder_issues=find_unresolved_placeholders(document),
        schema_errors=_schema_errors(document, resolved_schema_path),
    )


def load_execution_config(
    path: str | Path = default_config_path(),
    *,
    schema_path: str | Path = default_config_schema_path(),
) -> dict[str, Any]:
    """Load a config only when it is structurally valid and execution-ready."""

    config_path = Path(path)
    document = load_yaml(config_path)
    report = ConfigValidationReport(
        path=config_path,
        schema_path=Path(schema_path),
        placeholder_issues=find_unresolved_placeholders(document),
        schema_errors=_schema_errors(document, Path(schema_path)),
    )
    if report.schema_errors:
        raise ConfigurationError(
            "config validation failed: " + " | ".join(report.schema_errors)
        )
    if report.placeholder_issues:
        raise UnresolvedScientificPlaceholderError(report.placeholder_issues)
    # Null locks are represented explicitly rather than as string placeholders
    # so structural validation can remain useful.  They are still mandatory
    # execution gates and may never be silently interpreted as defaults.
    hardware = document.get("hardware", {})
    if not hardware.get("backend_selection"):
        raise ConfigurationError(
            "execution blocked: hardware.backend_selection must be selected by a recorded preflight"
        )
    return document


__all__ = [
    "ConfigValidationReport",
    "ConfigurationDependencyError",
    "ConfigurationError",
    "PlaceholderIssue",
    "UnresolvedScientificPlaceholderError",
    "default_config_path",
    "default_config_schema_path",
    "find_unresolved_placeholders",
    "load_execution_config",
    "load_yaml",
    "validate_config",
]
