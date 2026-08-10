from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolFunction = Callable[[dict[str,Any]], dict[str,Any]]

@dataclass(frozen=True)
class Tool:
    """
    Description and execution function for one agent tool.
    """

    name: str
    description: str
    input_schema: dict[str,Any]
    function: ToolFunction
