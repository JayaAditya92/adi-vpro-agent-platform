
import os
import re
from pathlib import Path


PROMPT_BASE_DIR = Path(__file__).resolve().parent / "prompts"


PROMPT_REGISTRY = {
    "rag_answer": {
        "folder": "rag",
        "environment_variable": "RAG_ANSWER_PROMPT_VERSION",
        "default_version": "v1",
    },
    "rag_rewrite": {
        "folder": "rewrite",
        "environment_variable": "RAG_REWRITE_PROMPT_VERSION",
        "default_version": "v1",
    },
    "mcp_agent": {
        "folder": "mcp_agent",
        "environment_variable": "MCP_AGENT_PROMPT_VERSION",
        "default_version": "v1",
    },
}


def get_prompt_version(prompt_name: str) -> str:
    if prompt_name not in PROMPT_REGISTRY:
        raise ValueError(f"Unknown prompt name: {prompt_name}")

    config = PROMPT_REGISTRY[prompt_name]

    version = os.getenv(
        config["environment_variable"],
        config["default_version"],
    ).strip()

    if not re.fullmatch(r"v[1-9][0-9]*", version):
        raise ValueError(
            f"Invalid prompt version for {prompt_name}: {version}"
        )

    return version


def load_prompt(prompt_name: str, version: str = None) -> str:
    if prompt_name not in PROMPT_REGISTRY:
        raise ValueError(f"Unknown prompt name: {prompt_name}")

    config = PROMPT_REGISTRY[prompt_name]

    selected_version = version or get_prompt_version(prompt_name)

    if not re.fullmatch(r"v[1-9][0-9]*", selected_version):
        raise ValueError(f"Invalid prompt version: {selected_version}")

    prompt_path = (
        PROMPT_BASE_DIR
        / config["folder"]
        / f"{selected_version}.txt"
    )

    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_name}/{selected_version}"
        )

    return prompt_path.read_text(encoding="utf-8")


def get_prompt_metadata(prompt_name: str) -> dict:
    version = get_prompt_version(prompt_name)

    return {
        "prompt_name": prompt_name,
        "version": version,
        "file": f"{PROMPT_REGISTRY[prompt_name]['folder']}/{version}.txt",
    }