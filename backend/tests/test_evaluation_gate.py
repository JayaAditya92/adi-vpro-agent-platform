
from app.evaluation_gate import evaluate_report


def create_sample_report():

    return {
        "total_records": 1,
        "successful_records": 1,
        "failed_records": 0,

        "average_ragas_scores": {
            "faithfulness": 0.98,
            "context_precision": 0.95,
            "context_recall": 0.95,
            "answer_relevance": 0.90,
            "answer_correctness": 0.95,
        },

        "results": [
            {
                "question": "What is Python?",
                "status": "success",

                "custom_metrics": {
                    "context_available": True,
                    "answer_is_empty": False,
                    "answer_length_valid": True,
                    "source_coverage": 1.0,
                    "keyword_match_score": 1.0,
                }
            }
        ]
    }


def test_valid_report_passes():
    report = create_sample_report()

    result = evaluate_report(report)

    assert result["gate_status"] == "PASS"
    assert result["failed_checks"] == 0


def test_low_faithfulness_fails():
    report = create_sample_report()

    report["average_ragas_scores"]["faithfulness"] = 0.70

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_low_answer_relevance_fails():
    report = create_sample_report()

    report["average_ragas_scores"]["answer_relevance"] = 0.50

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_failed_evaluation_record_fails():
    report = create_sample_report()

    report["successful_records"] = 0
    report["failed_records"] = 1
    report["results"][0]["status"] = "failed"

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_empty_answer_fails():
    report = create_sample_report()

    report["results"][0]["custom_metrics"]["answer_is_empty"] = True

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_missing_context_fails():
    report = create_sample_report()

    report["results"][0]["custom_metrics"]["context_available"] = False

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_low_keyword_match_fails():
    report = create_sample_report()

    report["results"][0]["custom_metrics"]["keyword_match_score"] = 0.50

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_missing_ragas_metric_fails():
    report = create_sample_report()

    del report["average_ragas_scores"]["faithfulness"]

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_inconsistent_record_counts_fail():
    report = create_sample_report()

    report["total_records"] = 5

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"


def test_invalid_score_fails():
    report = create_sample_report()

    report["average_ragas_scores"]["faithfulness"] = 1.5

    result = evaluate_report(report)

    assert result["gate_status"] == "FAIL"