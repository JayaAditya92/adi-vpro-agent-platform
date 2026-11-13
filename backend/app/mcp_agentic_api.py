from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.mcp_langgraph_agent import run_mcp_agent

router = APIRouter(
    prefix="/api/mcp-agent",
    tags=["MCP Agent"]
)

class MCPAgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

@router.post("/ask")
def ask_mcp_agent(request: MCPAgentRequest):
    try:
        result = run_mcp_agent(request.question)

        security = result.get("security", {})
        is_blocked = security.get("status") == "blocked"

        return {
            "status": "blocked" if is_blocked else "success",
            "question": request.question,
            "answer": result["answer"],
            "tool_calls": result["tool_calls"],
            "security": security,
            "prompt_version": result.get("prompt_version"),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"MCP Agent Error: {str(error)}"
        )