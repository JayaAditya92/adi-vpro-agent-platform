
import json
import math
from pathlib import Path


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_REPORT_PATH = (
    BASE_DIR / "reports" / "live_rag_evaluation_report.json"
)

RAGAS_THRESHOLDS = {
    "faithfulness": 0.95,
    "context_precision": 0.90,
    "context_recall": 0.90,
    "answer_relevance": 0.80,
    "answer_correctness": 0.90,
}

CUSTOM_THRESHOLDS = {
    "source_coverage": 0.90,
    "keyword_match_score": 0.90,
}


# --------------------------------------------------
# HELPER: VALIDATE NUMERIC SCORES
# --------------------------------------------------

def is_valid_score(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= value <= 1.0
    )


# --------------------------------------------------
# MAIN EVALUATION GATE
# --------------------------------------------------

def evaluate_report(report):

    checks = []

    def add_check(name, passed, actual=None, expected=None, message=""):
        checks.append({
            "name": name,
            "passed": bool(passed),
            "actual": actual,
            "expected": expected,
            "message": message,
        })

    # 1. Validate report structure
    if not isinstance(report, dict):
        add_check(
            "report_structure",
            False,
            message="Report must be a JSON object."
        )
        return build_result(checks)

    required_fields = [
        "total_records",
        "successful_records",
        "failed_records",
        "average_ragas_scores",
        "results",
    ]

    missing_fields = [
        field for field in required_fields
        if field not in report
    ]

    add_check(
        "report_structure",
        not missing_fields,
        actual=missing_fields,
        expected="All required report fields",
        message=(
            "Required report fields are present."
            if not missing_fields
            else f"Missing fields: {missing_fields}"
        )
    )

    if missing_fields:
        return build_result(checks)

    total = report["total_records"]
    successful = report["successful_records"]
    failed = report["failed_records"]
    results = report["results"]

    # 2. Validate record counts
    counts_valid = (
        isinstance(total, int)
        and not isinstance(total, bool)
        and isinstance(successful, int)
        and not isinstance(successful, bool)
        and isinstance(failed, int)
        and not isinstance(failed, bool)
        and total > 0
        and successful >= 0
        and failed >= 0
        and total == successful + failed
        and isinstance(results, list)
        and len(results) == total
    )

    add_check(
        "record_counts",
        counts_valid,
        actual={
            "total": total,
            "successful": successful,
            "failed": failed,
            "result_entries": len(results)
            if isinstance(results, list) else None,
        },
        expected="Valid counts and matching result entries",
        message=(
            "Evaluation record counts are valid."
            if counts_valid
            else "Evaluation record counts are inconsistent."
        )
    )

    if not counts_valid:
        return build_result(checks)

    # 3. Check failed records
    add_check(
        "failed_records",
        failed == 0,
        actual=failed,
        expected=0,
        message=(
            "No failed evaluation records."
            if failed == 0
            else "One or more evaluation records failed."
        )
    )

    # 4. Check successful records
    add_check(
        "successful_records",
        successful == total,
        actual=successful,
        expected=total,
        message=(
            "All evaluation records succeeded."
            if successful == total
            else "Not all evaluation records succeeded."
        )
    )

    # 5. Validate and check average RAGAS scores
    average_scores = report["average_ragas_scores"]

    if not isinstance(average_scores, dict):
        add_check(
            "ragas_score_structure",
            False,
            message="Average RAGAS scores must be an object."
        )
        return build_result(checks)

    for metric, threshold in RAGAS_THRESHOLDS.items():

        actual = average_scores.get(metric)

        passed = (
            is_valid_score(actual)
            and actual >= threshold
        )

        add_check(
            f"ragas_{metric}",
            passed,
            actual=actual,
            expected=threshold,
            message=(
                f"{metric} meets the required threshold."
                if passed
                else f"{metric} is missing, invalid, or below threshold."
            )
        )

    # 6. Validate every individual record
    for index, record in enumerate(results, start=1):

        if not isinstance(record, dict):
            add_check(
                f"record_{index}_structure",
                False,
                message="Evaluation record must be an object."
            )
            continue

        record_success = record.get("status") == "success"

        add_check(
            f"record_{index}_status",
            record_success,
            actual=record.get("status"),
            expected="success",
            message=(
                "Record succeeded."
                if record_success
                else "Record did not succeed."
            )
        )

        if not record_success:
            continue

        custom = record.get("custom_metrics")

        if not isinstance(custom, dict):
            add_check(
                f"record_{index}_custom_metrics",
                False,
                message="Custom metrics are missing or invalid."
            )
            continue

        # Context must be available
        add_check(
            f"record_{index}_context_available",
            custom.get("context_available") is True,
            actual=custom.get("context_available"),
            expected=True,
            message="Retrieved context must be available."
        )

        # Answer must not be empty
        add_check(
            f"record_{index}_answer_not_empty",
            custom.get("answer_is_empty") is False,
            actual=custom.get("answer_is_empty"),
            expected=False,
            message="Generated answer must not be empty."
        )

        # Answer length must be valid
        add_check(
            f"record_{index}_answer_length",
            custom.get("answer_length_valid") is True,
            actual=custom.get("answer_length_valid"),
            expected=True,
            message="Answer length must be valid."
        )

        # Validate custom keyword metrics when available
        for metric, threshold in CUSTOM_THRESHOLDS.items():

            actual = custom.get(metric)

            # None means no required keywords were supplied.
            if actual is None:
                continue

            passed = (
                is_valid_score(actual)
                and actual >= threshold
            )

            add_check(
                f"record_{index}_{metric}",
                passed,
                actual=actual,
                expected=threshold,
                message=(
                    f"{metric} meets the required threshold."
                    if passed
                    else f"{metric} is missing, invalid, or below threshold."
                )
            )

    return build_result(checks)


# --------------------------------------------------
# BUILD FINAL GATE RESULT
# --------------------------------------------------

def build_result(checks):

    failed_checks = [
        check for check in checks
        if not check["passed"]
    ]

    passed_checks = len(checks) - len(failed_checks)

    return {
        "gate_status": "PASS" if not failed_checks else "FAIL",
        "total_checks": len(checks),
        "passed_checks": passed_checks,
        "failed_checks": len(failed_checks),
        "checks": checks,
        "failure_reasons": [
            check["message"]
            for check in failed_checks
        ],
    }


# --------------------------------------------------
# LOAD AND EVALUATE REPORT FILE
# --------------------------------------------------

def evaluate_report_file(report_path=DEFAULT_REPORT_PATH):

    report_path = Path(report_path)

    if not report_path.is_file():
        return build_result([{
            "name": "report_file",
            "passed": False,
            "actual": str(report_path),
            "expected": "Existing evaluation report",
            "message": f"Report file not found: {report_path}",
        }])

    try:
        with open(report_path, "r", encoding="utf-8") as file:
            report = json.load(file)

    except (OSError, json.JSONDecodeError) as error:
        return build_result([{
            "name": "report_file",
            "passed": False,
            "actual": str(report_path),
            "expected": "Readable valid JSON report",
            "message": f"Unable to read evaluation report: {error}",
        }])

    return evaluate_report(report)