
import pytest

from app.prompt_manager import (
    load_prompt,
    get_prompt_version,
    get_prompt_metadata,
)


def test_load_rag_answer_prompt():
    prompt = load_prompt("rag_answer")

    assert "document-grounded AI teaching assistant" in prompt
    assert "{history}" in prompt
    assert "{context}" in prompt


def test_load_rewrite_prompt():
    prompt = load_prompt("rag_rewrite")

    assert "standalone search query" in prompt
    assert "{history}" in prompt
    assert "{question}" in prompt


def test_load_mcp_agent_prompt():
    prompt = load_prompt("mcp_agent")

    assert "VPRO Skills EduTech Agent" in prompt
    assert "untrusted data" in prompt


def test_load_specific_prompt_version():
    prompt = load_prompt("rag_answer", version="v1")

    assert "GROUNDING:" in prompt


def test_unknown_prompt_is_rejected():
    with pytest.raises(ValueError):
        load_prompt("unknown_prompt")


def test_invalid_prompt_version_is_rejected():
    with pytest.raises(ValueError):
        load_prompt("rag_answer", version="../secret")


def test_prompt_metadata():
    metadata = get_prompt_metadata("rag_answer")

    assert metadata["prompt_name"] == "rag_answer"
    assert metadata["version"] == "v1"
    assert metadata["file"] == "rag/v1.txt"


def test_unknown_prompt_version_lookup():
    with pytest.raises(ValueError):
        get_prompt_version("unknown_prompt")