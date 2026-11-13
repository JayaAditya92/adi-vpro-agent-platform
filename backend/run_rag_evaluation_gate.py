
import json
import sys

from app.evaluation_gate import evaluate_report_file


def main():

    print("\n" + "=" * 60)
    print("VPRO SKILLS - RAG EVALUATION GATE")
    print("=" * 60)

    result = evaluate_report_file()

    for check in result["checks"]:

        status = "PASS" if check["passed"] else "FAIL"

        print(f"[{status}] {check['name']}")

        if not check["passed"]:
            print(f"       Reason: {check['message']}")

    print("\n" + "=" * 60)

    print("Gate Status:", result["gate_status"])
    print("Total Checks:", result["total_checks"])
    print("Passed Checks:", result["passed_checks"])
    print("Failed Checks:", result["failed_checks"])

    print("=" * 60)

    if result["gate_status"] == "PASS":
        print("\nRAG EVALUATION GATE PASSED.")
        sys.exit(0)

    print("\nRAG EVALUATION GATE FAILED.")
    sys.exit(1)


if __name__ == "__main__":
    main()