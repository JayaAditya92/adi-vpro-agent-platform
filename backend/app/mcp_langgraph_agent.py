"""LangGraph agent that calls the VPRO MCP server with security checks."""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from app.prompt_manager import load_prompt, get_prompt_metadata
from app.rag_service import llm
from app.security_service import (
    moderation_check,
    redact_sensitive_data,
    validate_output,
)

MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


async def call_mcp_tool(tool_name: str, arguments: dict):
    """Call a named MCP tool after validating its arguments and sanitize output."""
    if tool_name == "calculator":
        expression = arguments.get("expression", "")
        check = moderation_check(expression)
        if not check["allowed"]:
            raise ValueError("Calculator input blocked by security checks.")

    elif tool_name == "search_knowledge_base":
        query = arguments.get("query", "")
        check = moderation_check(query)
        if not check["allowed"]:
            raise ValueError("Knowledge search input blocked by security checks.")

        top_k = arguments.get("top_k", 3)
        if not isinstance(top_k, int) or isinstance(top_k, bool) or not 1 <= top_k <= 8:
            raise ValueError("top_k must be an integer between 1 and 8.")

    else:
        raise ValueError("Requested MCP tool is not permitted.")

    async with streamablehttp_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
        get_session_id,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)

            if result.isError:
                raise RuntimeError(f"MCP tool failed: {tool_name}")

            output = []
            for item in result.content:
                if hasattr(item, "text"):
                    text_value, _ = redact_sensitive_data(item.text)
                    output.append(text_value)

            return "\n".join(output)


@tool
def mcp_calculator(expression: str) -> str:
    """Perform arithmetic calculations using the VPRO MCP server."""
    check = moderation_check(expression)
    if not check["allowed"]:
        return "Error: calculator input was blocked by security checks."

    try:
        return asyncio.run(call_mcp_tool(
            "calculator",
            {"expression": expression},
        ))
    except Exception:
        return "Error: calculator tool is temporarily unavailable."


@tool
def mcp_search_knowledge_base(query: str) -> str:
    """Search VPRO uploaded course documents through the MCP server."""
    check = moderation_check(query)
    if not check["allowed"]:
        return "Knowledge search was blocked by security checks."

    try:
        return asyncio.run(call_mcp_tool(
            "search_knowledge_base",
            {"query": query, "top_k": 3},
        ))
    except Exception:
        return "Knowledge search is temporarily unavailable."


mcp_tools = [mcp_calculator, mcp_search_knowledge_base]
llm_with_tools = llm.bind_tools(mcp_tools)

SYSTEM_MESSAGE = SystemMessage(
    content=load_prompt("mcp_agent")
)

def assistant_node(state: MessagesState):
    response = llm_with_tools.invoke(
        [SYSTEM_MESSAGE] + state["messages"]
    )
    return {"messages": [response]}


builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant_node)
builder.add_node("tools", ToolNode(mcp_tools))
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", tools_condition)
builder.add_edge("tools", "assistant")
mcp_agent_graph = builder.compile()


def run_mcp_agent(question: str):
    """Run the MCP-backed agent with input and output security checks."""
    check = moderation_check(question)
    if not check["allowed"]:
        return {
            "answer": "Request blocked by security checks.",
            "tool_calls": [],
            "security": {
                "status": "blocked",
                "category": check.get("category"),
                "reason": check["reason"],
            },
        }

    result = mcp_agent_graph.invoke(
        {"messages": [HumanMessage(content=question)]},
        config={"recursion_limit": 8},
    )

    messages = result["messages"]
    answer = ""

    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            answer = message.content
            break

    if isinstance(answer, list):
        answer = "\n".join(
            item.get("text", "")
            for item in answer
            if isinstance(item, dict)
        )

    validation = validate_output(str(answer))
    safe_answer = (
        validation["content"]
        if validation["safe"]
        else "The agent response did not pass output validation."
    )

    tool_calls = []
    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                tool_calls.append({
                    "tool": call["name"],
                    "arguments": call["args"],
                })

    return {
    "answer": safe_answer,
    "tool_calls": tool_calls,
    "security": {
        "status": "passed",
        "output_issues": validation.get("issues", []),
    },
    "prompt_version": get_prompt_metadata("mcp_agent"),
    }