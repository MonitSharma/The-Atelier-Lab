import json
from typing import Any

# pyrefly: ignore [missing-import]
from agent.brain import ask_model

from tools.calculator import CalculatorError, calculate

SYSTEM_PROMPT = """
You are a small local agent operating inside a Python program.
You have access to exactly one tool:
calculator(expression: string)
Use the calculator whenever the user asks for arithmetic.
You must return exactly one valid JSON object.
Do not include markdown fences.
Do not include explanations outside the JSON.
When you want to use the calculator, return:

{
  "type": "tool_call",
  "tool": "calculator",
  "arguments": {
    "expression": "the arithmetic expression"
  }
}
When you have enough information to answer the user, return:
{
  "type": "final",
  "answer": "your final answer"
}
Never invent a calculator result.
After receiving a tool result, use that result in the final answer.
""".strip()


class AgentError(RuntimeError):
    """Raised when the agent cannot complete a task successfully"""

def parse_model_response(raw_response: str) -> dict[str, Any]:
    """Parse the JSON response from the model."""
    
    cleaned = raw_response.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AgentError(
            f"The model did not return valid JSON:\n{raw_response}"
        ) from exc
    if not isinstance(decision, dict):
        raise AgentError("The model response must be a JSON object.")
    response_type = decision.get("type")
    if response_type not in {"tool_call", "final"}:
        raise AgentError(
            "The response type must be either 'tool_call' or 'final'."
        )
    return decision

def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate and execute a registered tool."""
    if tool_name != "calculator":

        return {
            "status": "error",
            "error_type": "unknown_tool",
            "message": f"Unknown tool: {tool_name}",
            "available_tools": ["calculator"],
        }

    expression = arguments.get("expression")
    if not isinstance(expression, str):

        return {
            "status": "error",
            "error_type": "invalid_arguments",
            "message": "The calculator requires a string argument named 'expression'.",
        }

    try:
        result = calculate(expression)
    except CalculatorError as exc:

        return {
            "status": "error",
            "error_type": "calculator_error",
            "message": str(exc),
        }

    return {
        "status": "success",
        "tool": "calculator",
        "expression": expression,
        "result": result,
    }

def run_agent(goal: str, max_steps: int = 5) -> str:
    """Run the perceive-plan-act-observe loop."""
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": goal,
        },
    ]
    trace: list[dict[str, Any]] = []

    for step in range(1, max_steps + 1):
        print(f"\n--- Step {step} ---")
        raw_response = ask_model(messages)
        
        step_trace: dict[str, object] = {
            "step" : step,
            "raw_model_response": raw_response
        }


        print("Model response:")
        print(raw_response)

        try:
            decision = parse_model_response(raw_response)
            step_trace["decision"] = decision
        except AgentError as exc:
            error_observation = {
                "status": "error",
                "error_type": "invalid_model_output",
                "message": str(exc),
                "instruction": (
                    "Return exactly one valid JSON object using the required schema."
                ),
            }
            step_trace["error"] = error_observation
            trace.append(step_trace)
            messages.append(
                {
                    "role": "assistant",
                    "content": raw_response,
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid.\n"
                        f"Error:\n{json.dumps(error_observation)}"
                    ),
                }
            )

            continue

        if decision["type"] == "final":
            answer = decision.get("answer")
            if not isinstance(answer, str):
                raise AgentError(
                    "A final response must contain a string field named 'answer'."
                )
            trace.append(step_trace)
            print("Trace:")
            print(json.dumps(trace, indent=2))
            return answer

        tool_name = decision.get("tool")
        arguments = decision.get("arguments")

        if not isinstance(tool_name, str):
            tool_result = {
                "status": "error",
                "error_type": "invalid_tool_name",
                "message": "The tool field must be a string.",
            }
        elif not isinstance(arguments, dict):
            tool_result = {
                "status": "error",
                "error_type": "invalid_arguments",
                "message": "The arguments field must be a JSON object.",
            }
        else:
            tool_result = execute_tool(tool_name, arguments)

        print("Tool result:")
        print(json.dumps(tool_result, indent=2))

        step_trace["tool_result"] = tool_result
        trace.append(step_trace)

        messages.append(
            {
                "role": "assistant",
                "content": raw_response,
            }
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "TOOL OBSERVATION:\n"
                    f"{json.dumps(tool_result)}\n\n"
                    "Use this observation to decide your next action."
                ),
            }
        )
    print("Trace:")
    print(json.dumps(trace, indent=2))
    raise AgentError(
        f"The agent did not finish within {max_steps} steps."
    )

if __name__ == "__main__":
    user_goal = input("Enter a goal: ")

    try:
        final_answer = run_agent(user_goal)
        print("\nFinal answer:")
        print(final_answer)

    except AgentError as exc:
        print("\nAgent failed:")
        print(exc)



