"""Lesson 10: VPRO MCP server (MCP Python SDK v1 compatibility line).

Exposes:
- calculator: safely evaluate basic arithmetic expressions.
- search_knowledge_base: retrieve relevant chunks from PostgreSQL + pgvector.

Run from the backend directory:
    python -m app.mcp_server
The Streamable HTTP MCP endpoint is http://127.0.0.1:8001/mcp
"""
import ast
import json
import operator
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import engine
from app.embedding_service import generate_embedding

# Load backend/.env explicitly, regardless of the current working directory.
from pathlib import Path
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

mcp = FastMCP(
    "VPRO Skills Knowledge Tools",
    instructions=(
        "Tools for arithmetic calculations and searching the VPRO Skills "
        "uploaded course-document knowledge base."
    ),
    host="127.0.0.1",
    port=8001
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def _evaluate_math(node):
    if isinstance(node, ast.Expression):
        return _evaluate_math(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate_math(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left = _evaluate_math(node.left)
        right = _evaluate_math(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Exponent must be between -8 and 8.")
        result = _ALLOWED_OPERATORS[type(node.op)](left, right)
        if abs(result) > 1e100:
            raise ValueError("The result is too large.")
        return result
    raise ValueError("Only basic arithmetic is supported: +, -, *, /, //, %, and **.")


@mcp.tool()
def calculator(expression: str) -> str:
    """Calculate a basic arithmetic expression, for example (25 * 4) + 10."""
    if not expression or len(expression) > 100:
        return "Error: expression must contain 1 to 100 characters."
    try:
        parsed = ast.parse(expression, mode="eval")
        return str(_evaluate_math(parsed))
    except ZeroDivisionError:
        return "Error: division by zero."
    except Exception as exc:
        return f"Error: {exc}"


@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """Search uploaded VPRO course documents for evidence relevant to a query."""
    query = (query or "").strip()
    if not query:
        return json.dumps({"results": [], "message": "Search query is empty."})
    if top_k < 1 or top_k > 8:
        return json.dumps({"results": [], "message": "top_k must be between 1 and 8."})

    db = SessionLocal()
    try:
        query_vector = generate_embedding(query)
        distance = models.DocumentChunk.embedding.cosine_distance(query_vector)
        rows = (
            db.query(
                models.DocumentChunk,
                models.Document.filename,
                distance.label("distance"),
            )
            .join(
                models.Document,
                models.Document.id == models.DocumentChunk.document_id,
            )
            .order_by(distance.asc())
            .limit(top_k)
            .all()
        )

        max_distance = float(os.getenv("RAG_MAX_COSINE_DISTANCE", "0.65"))
        results = []
        for chunk, filename, cosine_distance in rows:
            distance_value = float(cosine_distance)
            if distance_value <= max_distance:
                results.append(
                    {
                        "document_id": chunk.document_id,
                        "filename": filename,
                        "chunk_number": chunk.chunk_number,
                        "content": chunk.content,
                        "cosine_distance": round(distance_value, 4),
                    }
                )
        return json.dumps(
            {"query": query, "count": len(results), "results": results},
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"query": query, "results": [], "error": str(exc)})
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")