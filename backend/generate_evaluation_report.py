
import json
from pathlib import Path
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent

REPORT_PATH = (
    BASE_DIR / "reports" / "rag_evaluation_report.json"
)

OUTPUT_PATH = (
    BASE_DIR / "reports" / "rag_evaluation_summary.md"
)


def generate_report():

    if not REPORT_PATH.exists():
        raise FileNotFoundError(
            "Run evaluate_dataset.py before generating the report."
        )

    with open(REPORT_PATH, "r", encoding="utf-8") as file:
        report = json.load(file)

    lines = []

    lines.append("# VPRO Skills – RAG Evaluation Report")
    lines.append("")
    lines.append(
        f"**Project:** {report.get('project', 'VPRO Skills Agentic AI')}"
    )
    lines.append(
        f"**Evaluation Date:** {report.get('evaluation_date', 'Not available')}"
    )
    lines.append("")

    lines.append("## 1. Evaluation Overview")
    lines.append("")
    lines.append(f"- Total records: {report['total_records']}")
    lines.append(f"- Successful records: {report['successful_records']}")
    lines.append(f"- Failed records: {report['failed_records']}")
    lines.append("")

    lines.append("## 2. Average RAGAS Scores")
    lines.append("")
    lines.append("| Metric | Average Score |")
    lines.append("|---|---:|")

    for metric, score in report["average_ragas_scores"].items():

        display_score = (
            f"{score:.4f}" if score is not None else "N/A"
        )

        lines.append(f"| {metric} | {display_score} |")

    lines.append("")
    lines.append("## 3. Individual Evaluation Results")
    lines.append("")

    for index, result in enumerate(report["results"], start=1):

        lines.append(f"### Record {index}")
        lines.append("")

        lines.append(
            f"**Question:** {result.get('question', 'N/A')}"
        )
        lines.append("")

        lines.append(
            f"**Status:** {result.get('status', 'unknown')}"
        )
        lines.append("")

        if result.get("status") == "success":

            lines.append("**RAGAS Metrics**")
            lines.append("")
            lines.append("| Metric | Score |")
            lines.append("|---|---:|")

            for metric, score in result["ragas_metrics"].items():
                lines.append(f"| {metric} | {score:.4f} |")

            lines.append("")

            lines.append("**Custom Metrics**")
            lines.append("")

            for metric, value in result["custom_metrics"].items():
                lines.append(f"- **{metric}:** {value}")

            lines.append("")

        else:
            lines.append(
                f"**Error:** {result.get('error', 'Unknown error')}"
            )
            lines.append("")

    lines.append("## 4. Evaluation Conclusion")
    lines.append("")
    lines.append(
        "Review the individual metric scores to identify retrieval, "
        "grounding, relevance and answer-quality improvements."
    )
    lines.append("")

    lines.append(
        f"*Report generated: {datetime.now(timezone.utc).isoformat()}*"
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

    print("Evaluation summary generated successfully.")
    print("Report location:", OUTPUT_PATH)


if __name__ == "__main__":
    generate_report()