
import pytest

from app.agent_evaluation_gate import evaluate_agent_result


def test_tool_agent_valid_calculator_result_passes():
    result = {
        "answer": "The result is 25.",
        "tool_calls": [
            {
                "name": "calculator",
                "args": {"expression": "5 * 5"}
            }
        ],
        "security": {"status": "passed", "output_issues": []}
    }

    report = evaluate_agent_result(
        agent_type="tool_agent",
        result=result,
        expected_tools=["calculator"],
        expected_answer_keywords=["25"]
    )

    assert report["gate_status"] == "PASS"


def test_mcp_agent_valid_calculator_result_passes():
    result = {
        "answer": "The result is 20.",
        "tool_calls": [
            {
                "tool": "mcp_calculator",
                "arguments": {"expression": "4 * 5"}
            }
        ],
        "security": {"status": "passed", "output_issues": []},
        "prompt_version": "v1"
    }

    report = evaluate_agent_result(
        agent_type="mcp_agent",
        result=result,
        expected_tools=["mcp_calculator"],
        expected_answer_keywords=["20"]
    )

    assert report["gate_status"] == "PASS"


def test_mcp_agent_search_tool_passes():
    result = {
        "answer": "Python is a programming language.",
        "tool_calls": [
            {
                "tool": "mcp_search_knowledge_base",
                "arguments": {"query": "Python"}
            }
        ],
        "security": {"status": "passed", "output_issues": []}
    }

    report = evaluate_agent_result(
        agent_type="mcp_agent",
        result=result,
        expected_tools=["mcp_search_knowledge_base"]
    )

    assert report["gate_status"] == "PASS"


def test_unknown_tool_fails():
    result = {
        "answer": "Completed.",
        "tool_calls": [
            {
                "name": "unknown_tool",
                "args": {}
            }
        ],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result("tool_agent", result)

    assert report["gate_status"] == "FAIL"


def test_invalid_calculator_arguments_fail():
    result = {
        "answer": "Completed.",
        "tool_calls": [
            {
                "name": "calculator",
                "args": {"expression": ""}
            }
        ],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result("tool_agent", result)

    assert report["gate_status"] == "FAIL"


def test_missing_expected_tool_fails():
    result = {
        "answer": "Here is the answer.",
        "tool_calls": [],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result(
        "tool_agent",
        result,
        expected_tools=["calculator"]
    )

    assert report["gate_status"] == "FAIL"


def test_missing_answer_keyword_fails():
    result = {
        "answer": "The calculation is complete.",
        "tool_calls": [],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result(
        "tool_agent",
        result,
        expected_answer_keywords=["Python"]
    )

    assert report["gate_status"] == "FAIL"


def test_blocked_request_without_tool_calls_passes():
    result = {
        "answer": "I can't process this request because it was blocked by security checks.",
        "tool_calls": [],
        "security": {
            "status": "blocked",
            "category": "prompt_injection",
            "reason": "Security policy violation"
        }
    }

    report = evaluate_agent_result(
        "tool_agent",
        result,
        expected_security_status="blocked"
    )

    assert report["gate_status"] == "PASS"


def test_blocked_request_with_tool_calls_fails():
    result = {
        "answer": "Request blocked.",
        "tool_calls": [
            {
                "name": "calculator",
                "args": {"expression": "2 + 2"}
            }
        ],
        "security": {"status": "blocked"}
    }

    report = evaluate_agent_result(
        "tool_agent",
        result,
        expected_security_status="blocked"
    )

    assert report["gate_status"] == "FAIL"


def test_normal_request_with_blocked_security_status_fails():
    result = {
        "answer": "The result is 10.",
        "tool_calls": [],
        "security": {"status": "blocked"}
    }

    report = evaluate_agent_result(
        "tool_agent",
        result,
        expected_security_status="passed"
    )

    assert report["gate_status"] == "FAIL"


def test_missing_answer_fails():
    result = {
        "answer": "",
        "tool_calls": [],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result("tool_agent", result)

    assert report["gate_status"] == "FAIL"


def test_invalid_agent_type_fails():
    result = {
        "answer": "Completed.",
        "tool_calls": [],
        "security": {"status": "passed"}
    }

    report = evaluate_agent_result("invalid_agent", result)

    assert report["gate_status"] == "FAIL"