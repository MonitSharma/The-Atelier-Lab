from tools.registry import create_default_registry



def test_registered_calculator()-> None:
    registry = create_default_registry()

    result = registry.execute(
            "calculator",
            {
                "expression": "12*8",
                },
            )

    assert result["status"] == "success"
    assert result["result"] == 96


def test_unknown_tool() -> None:
    registry = create_default_registry()

    result = registry.execute(
            "nonexistent_tool",
            {},
            )
    
    assert result["status"] == "error"
    assert result["error_type"] == "unknown_tool"


def test_invalid_calculator_argument() -> None:
    registry = create_default_registry()

    result = registry.execute(
            "calculator",
            {
                "wrong_argument": "2+2",
                },
            )

    assert result["status"] == "error"
    assert result["error_type"] == "invalid_argument"

    
def test_default_registry_contains_read_file() -> None:
    registry = create_default_registry()
    tool_names = [tool.name for tool in registry.list_tools()]

    assert "calculator" in tool_names
    assert "read_file" in tool_names



registry = create_default_registry()

print(
        registry.execute(
            "calculator",
            {
                "expression":"12*8"},
            )
        )

print(
        registry.execute(
            "missing_tool",
            {},
            )
        )

print(registry.prompt_description())


