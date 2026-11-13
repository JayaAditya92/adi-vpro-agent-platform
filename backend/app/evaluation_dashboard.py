
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/evaluation",
    tags=["RAG Evaluation Dashboard"]
)

REPORTS_DIR = (
    Path(__file__).resolve().parent.parent / "reports"
)


def _read_report(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read evaluation report: {path.name}"
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid report format: {path.name}"
        )

    return data


def _report_summary(
    path: Path,
    data: dict[str, Any]
) -> dict[str, Any]:

    scores = data.get("average_ragas_scores") or {}

    return {
        "report_name": path.name,
        "project": data.get(
            "project",
            "RAG Evaluation"
        ),
        "evaluation_date": data.get("evaluation_date"),
        "evaluation_type": data.get("evaluation_type"),
        "total_records": data.get(
            "total_records",
            len(data.get("results", []))
        ),
        "successful_records": data.get(
            "successful_records",
            0
        ),
        "failed_records": data.get(
            "failed_records",
            0
        ),
        "average_ragas_scores": scores,
        "report_kind": (
            "agent" if "pass_percentage" in data else "rag"
        ),
        "total_test_cases": data.get("total_test_cases"),
        "passed_test_cases": data.get("passed_test_cases"),
        "failed_test_cases": data.get("failed_test_cases"),
        "pass_percentage": data.get("pass_percentage"),
        "overall_status": data.get("overall_status"),
    }


@router.get("/reports")
def list_evaluation_reports():
    """
    List JSON evaluation reports from backend/reports.
    """

    if not REPORTS_DIR.exists():
        return {
            "status": "success",
            "total_reports": 0,
            "reports": []
        }

    summaries = []

    for path in REPORTS_DIR.glob("*.json"):

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            if isinstance(data, dict) and (
                "average_ragas_scores" in data
                or "results" in data
            ):
                summaries.append(
                    _report_summary(path, data)
                )

        except (OSError, json.JSONDecodeError):
            # Ignore unrelated or incomplete JSON files.
            continue

    summaries.sort(
        key=lambda item: (
            item.get("evaluation_date") or ""
        ),
        reverse=True
    )

    return {
        "status": "success",
        "total_reports": len(summaries),
        "reports": summaries
    }


@router.get("/latest")
def get_latest_evaluation_report():
    """
    Return the newest evaluation report.
    """

    if not REPORTS_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail="Evaluation reports folder not found."
        )

    candidates = []

    for path in REPORTS_DIR.glob("*.json"):

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )

            if (
                isinstance(data, dict)
                and isinstance(data.get("results"), list)
            ):
                candidates.append(
                    (
                        data.get("evaluation_date") or "",
                        path,
                        data
                    )
                )

        except (OSError, json.JSONDecodeError):
            continue

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No evaluation reports found."
        )

    _, path, data = max(
        candidates,
        key=lambda item: item[0]
    )

    result = _report_summary(path, data)

    result["results"] = data.get("results", [])

    return {
        "status": "success",
        "report": result
    }


@router.get("/reports/{report_name}")
def get_evaluation_report(report_name: str):
    """
    Return one specific evaluation report.
    Only JSON files directly inside reports/ are allowed.
    """

    if (
        not report_name.endswith(".json")
        or Path(report_name).name != report_name
        or "/" in report_name
        or "\\" in report_name
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid report filename."
        )

    path = REPORTS_DIR / report_name

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Evaluation report not found."
        )

    data = _read_report(path)

    result = _report_summary(path, data)

    result["results"] = data.get("results", [])

    return {
        "status": "success",
        "report": result
    }