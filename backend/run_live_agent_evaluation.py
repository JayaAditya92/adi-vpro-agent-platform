
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.database import SessionLocal
from app.agentic_tools import run_tool_agent
from app.mcp_langgraph_agent import run_mcp_agent
from app.agent_evaluation_gate import evaluate_agent_result


BASE_DIR = Path(__file__).resolve().parent

DATASET_FILE = BASE_DIR / "data" / "agent_evaluation_dataset.json"

REPORT_DIR = BASE_DIR / "reports"

REPORT_FILE = REPORT_DIR / "live_agent_evaluation_report.json"


def load_dataset():
    """Load and validate the evaluation dataset."""

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATASET_FILE}"
        )

    with open(DATASET_FILE, "r", encoding="utf-8") as file:
        dataset = json.load(file)

    test_cases = dataset.get("test_cases")

    if not isinstance(test_cases, list) or not test_cases:
        raise ValueError("Dataset must contain a non-empty test_cases list.")

    return dataset


def execute_agent(test_case):
    """Execute the selected live agent."""

    agent_type = test_case["agent_type"]
    question = test_case["question"]

    if agent_type == "tool_agent":
        db = SessionLocal()

        try:
            return run_tool_agent(
                question=question,
                history=[],
                db=db,
            )
        finally:
            db.close()

    if agent_type == "mcp_agent":
        return run_mcp_agent(question)

    raise ValueError(f"Unsupported agent type: {agent_type}")


def evaluate_test_case(test_case):
    """Execute one scenario and evaluate its actual result."""

    print("\n" + "=" * 65)
    print(f"Test ID : {test_case['id']}")
    print(f"Agent   : {test_case['agent_type']}")
    print(f"Category: {test_case['category']}")
    print(f"Question: {test_case['question']}")

    try:
        agent_result = execute_agent(test_case)

        gate_result = evaluate_agent_result(
            agent_type=test_case["agent_type"],
            result=agent_result,
            expected_tools=test_case.get("expected_tools"),
            expected_answer_keywords=test_case.get(
                "expected_answer_keywords"
            ),
            expected_security_status=test_case.get(
                "expected_security_status",
                "passed",
            ),
        )

        print(f"Agent Answer: {agent_result.get('answer', '')}")
        print(f"Tool Calls  : {agent_result.get('tool_calls', [])}")
        print(f"Gate Status : {gate_result['gate_status']}")

        if gate_result["failure_reasons"]:
            for reason in gate_result["failure_reasons"]:
                print(f"Failure: {reason}")

        return {
            "test_id": test_case["id"],
            "agent_type": test_case["agent_type"],
            "category": test_case["category"],
            "question": test_case["question"],
            "agent_result": agent_result,
            "evaluation": gate_result,
            "execution_error": None,
        }

    except Exception as error:
        print(f"Execution Error: {type(error).__name__}: {error}")

        return {
            "test_id": test_case["id"],
            "agent_type": test_case["agent_type"],
            "category": test_case["category"],
            "question": test_case["question"],
            "agent_result": None,
            "evaluation": {
                "gate_status": "FAIL",
                "failure_reasons": [
                    "Agent execution failed."
                ],
            },
            "execution_error": (
                f"{type(error).__name__}: {error}"
            ),
        }


def generate_report(dataset, results):
    """Generate and save the evaluation report."""

    total = len(results)

    passed = sum(
        1 for item in results
        if item["evaluation"]["gate_status"] == "PASS"
    )

    failed = total - passed

    report = {
        "project": dataset.get("project"),
        "evaluation_date": datetime.now(
            timezone.utc
        ).isoformat(),
        "evaluation_type": "live_agent_evaluation",
        "total_test_cases": total,
        "passed_test_cases": passed,
        "failed_test_cases": failed,
        "pass_percentage": round(
            (passed / total) * 100, 2
        ) if total else 0,
        "overall_status": "PASS" if failed == 0 else "FAIL",
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return report


def main():
    print("\nVPRO SKILLS - LIVE AGENT EVALUATION")
    print("=" * 65)

    try:
        dataset = load_dataset()

        results = []

        for test_case in dataset["test_cases"]:
            result = evaluate_test_case(test_case)
            results.append(result)

        report = generate_report(dataset, results)

        print("\n" + "=" * 65)
        print("LIVE AGENT EVALUATION SUMMARY")
        print("=" * 65)

        print(f"Total Test Cases : {report['total_test_cases']}")
        print(f"Passed           : {report['passed_test_cases']}")
        print(f"Failed           : {report['failed_test_cases']}")
        print(f"Pass Percentage  : {report['pass_percentage']}%")
        print(f"Overall Status   : {report['overall_status']}")

        print(f"\nReport saved at:\n{REPORT_FILE}")

        if report["overall_status"] == "PASS":
            print("\nLIVE AGENT EVALUATION PASSED.")
            return 0

        print("\nLIVE AGENT EVALUATION FAILED.")
        return 1

    except Exception as error:
        print(
            f"\nEvaluation setup failed: "
            f"{type(error).__name__}: {error}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())