
import re


# --------------------------------------------------
# ALLOWED TOOLS
# --------------------------------------------------

ALLOWED_TOOLS = {
    "tool_agent": {
        "calculator",
        "search_knowledge_base",
    },
    "mcp_agent": {
        "mcp_calculator",
        "mcp_search_knowledge_base",
    },
}


# --------------------------------------------------
# TEXT MATCHING
# --------------------------------------------------

def normalize_text(text):
    return re.findall(r"\b[a-z0-9]+\b", str(text).lower())


def contains_phrase(text, phrase):

    text_tokens = normalize_text(text)
    phrase_tokens = normalize_text(phrase)

    if not phrase_tokens:
        return False

    size = len(phrase_tokens)

    return any(
        text_tokens[index:index + size] == phrase_tokens
        for index in range(len(text_tokens) - size + 1)
    )


# --------------------------------------------------
# NORMALIZE TOOL CALLS
# --------------------------------------------------

def normalize_tool_calls(agent_type, tool_calls):

    normalized = []

    for call in tool_calls:

        if not isinstance(call, dict):
            normalized.append({
                "name": None,
                "arguments": None,
            })
            continue

        if agent_type == "tool_agent":
            name = call.get("name")
            arguments = call.get("args")

        else:
            name = call.get("tool")
            arguments = call.get("arguments")

        normalized.append({
            "name": name,
            "arguments": arguments,
        })

    return normalized


# --------------------------------------------------
# VALIDATE TOOL ARGUMENTS
# --------------------------------------------------

def validate_tool_arguments(tool_name, arguments):

    if not isinstance(arguments, dict):
        return False

    if tool_name in {"calculator", "mcp_calculator"}:

        expression = arguments.get("expression")

        return (
            isinstance(expression, str)
            and bool(expression.strip())
            and len(expression) <= 100
        )

    if tool_name == "search_knowledge_base":

        query = arguments.get("query")

        return (
            isinstance(query, str)
            and bool(query.strip())
        )

    if tool_name == "mcp_search_knowledge_base":

        query = arguments.get("query")
        top_k = arguments.get("top_k", 3)

        return (
            isinstance(query, str)
            and bool(query.strip())
            and isinstance(top_k, int)
            and not isinstance(top_k, bool)
            and 1 <= top_k <= 8
        )

    return False


# --------------------------------------------------
# BUILD EVALUATION RESULT
# --------------------------------------------------

def build_result(checks):

    failed_checks = [
        check for check in checks
        if not check["passed"]
    ]

    return {
        "gate_status": "PASS" if not failed_checks else "FAIL",
        "total_checks": len(checks),
        "passed_checks": len(checks) - len(failed_checks),
        "failed_checks": len(failed_checks),
        "checks": checks,
        "failure_reasons": [
            check["message"]
            for check in failed_checks
        ],
    }


# --------------------------------------------------
# MAIN AGENT EVALUATION
# --------------------------------------------------

def evaluate_agent_result(
    agent_type,
    result,
    expected_tools=None,
    expected_answer_keywords=None,
    expected_security_status="passed",
):

    checks = []

    def add_check(name, passed, actual=None, expected=None, message=""):
        checks.append({
            "name": name,
            "passed": bool(passed),
            "actual": actual,
            "expected": expected,
            "message": message,
        })

    # 1. Validate agent type
    if agent_type not in ALLOWED_TOOLS:

        add_check(
            "agent_type",
            False,
            actual=agent_type,
            expected=list(ALLOWED_TOOLS.keys()),
            message="Unsupported agent type."
        )

        return build_result(checks)

    # 2. Validate response structure
    if not isinstance(result, dict):

        add_check(
            "result_structure",
            False,
            message="Agent result must be a dictionary."
        )

        return build_result(checks)

    answer = result.get("answer")
    tool_calls = result.get("tool_calls")
    security = result.get("security")

    add_check(
        "answer_present",
        isinstance(answer, str) and bool(answer.strip()),
        actual=answer,
        expected="Non-empty string",
        message="Agent answer must be non-empty text."
    )

    add_check(
        "tool_calls_structure",
        isinstance(tool_calls, list),
        actual=type(tool_calls).__name__,
        expected="list",
        message="Tool calls must be returned as a list."
    )

    add_check(
        "security_structure",
        isinstance(security, dict),
        actual=type(security).__name__,
        expected="dict",
        message="Security information must be available."
    )

    if not isinstance(tool_calls, list) or not isinstance(security, dict):
        return build_result(checks)

    # 3. Validate security status
    actual_security_status = security.get("status")

    security_passed = (
        actual_security_status == expected_security_status
    )

    add_check(
        "security_status",
        security_passed,
        actual=actual_security_status,
        expected=expected_security_status,
        message="Agent security status does not match expectation."
    )

    # 4. Normalize tool calls
    normalized_calls = normalize_tool_calls(
        agent_type,
        tool_calls
    )

    allowed_tools = ALLOWED_TOOLS[agent_type]

    actual_tool_names = [
        call["name"]
        for call in normalized_calls
    ]

    # 5. Validate tool names
    unknown_tools = [
        name for name in actual_tool_names
        if name not in allowed_tools
    ]

    add_check(
        "allowed_tools",
        not unknown_tools,
        actual=actual_tool_names,
        expected=sorted(allowed_tools),
        message=(
            "Only permitted tools were used."
            if not unknown_tools
            else f"Unknown tools detected: {unknown_tools}"
        )
    )

    # 6. Validate each tool call
    for index, call in enumerate(normalized_calls, start=1):

        name = call["name"]
        arguments = call["arguments"]

        valid_name = name in allowed_tools

        arguments_valid = (
            valid_name
            and validate_tool_arguments(name, arguments)
        )

        add_check(
            f"tool_call_{index}_arguments",
            arguments_valid,
            actual=arguments,
            expected="Valid arguments for the selected tool",
            message=f"Invalid arguments for tool call {index}."
        )

    # 7. Validate expected tool calls
    if expected_tools is not None:

        if not isinstance(expected_tools, list):
            add_check(
                "expected_tools",
                False,
                actual=expected_tools,
                expected="List of expected tool names",
                message="expected_tools must be a list."
            )

        else:
            missing_tools = [
                tool_name for tool_name in expected_tools
                if tool_name not in actual_tool_names
            ]

            add_check(
                "expected_tools",
                not missing_tools,
                actual=actual_tool_names,
                expected=expected_tools,
                message=(
                    "All expected tools were called."
                    if not missing_tools
                    else f"Expected tools not called: {missing_tools}"
                )
            )

    # 8. Blocked requests must not execute tools
    if expected_security_status == "blocked":

        add_check(
            "blocked_request_no_tool_execution",
            len(tool_calls) == 0,
            actual=len(tool_calls),
            expected=0,
            message="Blocked requests must not execute tools."
        )

    # 9. Validate expected answer keywords
    if expected_answer_keywords is not None:

        if not isinstance(expected_answer_keywords, list):

            add_check(
                "answer_keywords",
                False,
                actual=expected_answer_keywords,
                expected="List of expected keywords",
                message="Expected answer keywords must be a list."
            )

        elif isinstance(answer, str):

            missing_keywords = [
                keyword
                for keyword in expected_answer_keywords
                if not contains_phrase(answer, keyword)
            ]

            add_check(
                "answer_keywords",
                not missing_keywords,
                actual=answer,
                expected=expected_answer_keywords,
                message=(
                    "Expected answer keywords were found."
                    if not missing_keywords
                    else f"Missing answer keywords: {missing_keywords}"
                )
            )

    return build_result(checks)