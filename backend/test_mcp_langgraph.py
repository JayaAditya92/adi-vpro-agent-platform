from app.mcp_langgraph_agent import run_mcp_agent


def test_agent(question):

    print("\nUSER QUESTION:")
    print(question)

    result = run_mcp_agent(question)

    print("\nTOOL CALLS:")
    print(result["tool_calls"])

    print("\nAGENT ANSWER:")
    print(result["answer"])


if __name__ == "__main__":

    test_agent(
        "Calculate 250 multiplied by 4 plus 150."
    )

    test_agent(
        "What are the main features of Python? "
        "Use my uploaded knowledge documents."
    )