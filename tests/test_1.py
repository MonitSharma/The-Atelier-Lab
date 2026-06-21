from dataclasses import dataclass

from agent.loop import AgentError, run_agent


@dataclass
class SmokeTest:
    name: str
    prompt: str
    expected_text: str


TESTS = [
    SmokeTest(
        name="basic multiplication",
        prompt="Use the calculator to calculate 173 multiplied by 284.",
        expected_text="49132",
    ),
    SmokeTest(
        name="parentheses and precedence",
        prompt="Use the calculator to calculate (144 / 12 + 7) * 13.",
        expected_text="247",
    ),
    SmokeTest(
        name="subtraction after multiplication",
        prompt="Use the calculator to calculate (3817 * 94) - 628.",
        expected_text="358170",
    ),
    SmokeTest(
        name="division",
        prompt="Use the calculator to calculate (9876 - 4321) / 5.",
        expected_text="1111",
    ),
    SmokeTest(
        name="powers",
        prompt="Use the calculator to calculate 2**18 + 2**12.",
        expected_text="266240",
    ),
]


def normalize(text: str) -> str:
    """Remove common formatting differences before comparison."""

    return (
        text.lower()
        .replace(",", "")
        .replace(" ", "")
        .replace("\n", "")
    )


def run_smoke_tests() -> None:
    passed = 0

    for index, test in enumerate(TESTS, start=1):
        print(f"\n{'=' * 60}")
        print(f"Test {index}: {test.name}")
        print(f"Prompt: {test.prompt}")

        try:
            answer = run_agent(test.prompt)
        except AgentError as exc:
            print("Result: FAIL")
            print(f"Agent error: {exc}")
            continue
        except Exception as exc:
            print("Result: FAIL")
            print(f"Unexpected error: {type(exc).__name__}: {exc}")
            continue

        print(f"Answer: {answer}")

        if normalize(test.expected_text) in normalize(answer):
            print("Result: PASS")
            passed += 1
        else:
            print("Result: FAIL")
            print(f"Expected answer to contain: {test.expected_text}")

    print(f"\n{'=' * 60}")
    print(f"Smoke-test result: {passed}/{len(TESTS)} passed")

    if passed == len(TESTS):
        print("Phase 0 smoke tests passed.")
    else:
        print("Some tests failed. Inspect the traces above.")


if __name__ == "__main__":
    run_smoke_tests()