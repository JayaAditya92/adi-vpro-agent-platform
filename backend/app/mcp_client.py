import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


async def main():
    print("\nConnecting to VPRO MCP Server...")

    try:
        async with streamablehttp_client(
            MCP_SERVER_URL
        ) as (read_stream, write_stream, get_session_id):

            async with ClientSession(
                read_stream,
                write_stream
            ) as session:

                # Initialize MCP connection
                await session.initialize()

                print("\nMCP connection successful!")

                # Discover available tools
                tools_response = await session.list_tools()

                print("\nAvailable MCP Tools:")

                for tool in tools_response.tools:
                    print(f"- {tool.name}: {tool.description}")

                # Test calculator tool
                print("\nTesting Calculator...")

                calculator_result = await session.call_tool(
                    "calculator",
                    arguments={
                        "expression": "(250 * 4) + 150"
                    }
                )

                print("\nCalculator Result:")

                for item in calculator_result.content:
                    if hasattr(item, "text"):
                        print(item.text)

                # Test knowledge search tool
                print("\nTesting Knowledge Base Search...")

                search_result = await session.call_tool(
                    "search_knowledge_base",
                    arguments={
                        "query": "What are the main features of Python?",
                        "top_k": 3
                    }
                )

                print("\nKnowledge Search Result:")

                for item in search_result.content:
                    if hasattr(item, "text"):
                        print(item.text)

    except Exception as error:
        print("\nMCP Client Error:")
        print(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    asyncio.run(main())