import ast
import operator
from typing import Final, Any
from tools.base import Tool


_BINARY_OPERATORS: Final = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_UNARY_OPERATORS: Final = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorError(ValueError):
    """Raised when an expression is invalid"""

def calculate(expression: str) -> int | float :
    """ Safely evaluate a basic arithmetic expression using ast"""
    
    if not expression.strip():
        raise CalculatorError("The Expression cannot be empty")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CalculatorError("The expression is not valid arithmetic.") from exc

    try:
        return _evaluate_node(tree.body)
    except ZeroDivisionError as exc:
        raise CalculatorError("Division by zero is not allowed.") from exc

def _evaluate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(
            node.value, (int, float)
        ):

            raise CalculatorError("Only numbers are allowed.")
        return node.value

    if isinstance(node, ast.BinOp):
        operator_function = _BINARY_OPERATORS.get(type(node.op))
        if operator_function is None:
            raise CalculatorError("That arithmetic operator is not supported.")
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        return operator_function(left, right)

    if isinstance(node, ast.UnaryOp):
        operator_function = _UNARY_OPERATORS.get(type(node.op))
        if operator_function is None:
            raise CalculatorError("That unary operator is not supported.")
        return operator_function(_evaluate_node(node.operand))
    raise CalculatorError(
        "Only numbers, parentheses, and arithmetic operators are allowed."
    )


def run_calculator(arguments: dict[str,Any]) -> dict[str,Any]:
    """Excute the calculator tool using validated arguments"""
    expression = arguments.get("expression")

    if not isinstance(expression, str):
        return {
                "status":"error",
                "error_type": "invalid_argument",
                "message": (
                    "The calculator requires a string argument named 'Expression'."
                    )
                }

    try:
        result = calculate(expression)
    except CalculatorError as exc:
        return {
                "status": "error",
                "error_type": "calculate_error",
                "message" : str(exc),
                }

    return {
            "status": "success",
            "tool": "calculator",
            "expression": expression,
            "result": result,
            }



CALCULATOR_TOOL = Tool(
        name="calculator",
        description= (
            "Safely evaluate a basic arithmetic expression. "
            "Supports addition, subtraction, multiplication, division, "
            "floor division, modulo, exponentiation, and parantheses."
            ),

        input_schema= {
            "type" : "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression to evaluate.",
                    }
                },
            "required": ["expression"],
            "additionalProperties":False,
            },
        function=run_calculator
        )



if __name__ == "__main__":
    tests = [
        "2 * 3 * 4",
        "(17 * 5) ** 2",
        "3817 * 94",
        "(9876 - 4321) / 5",
    ]

    for test in tests:
        print(f"{test} = {calculate(test)}")
