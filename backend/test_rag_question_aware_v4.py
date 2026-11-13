import ast
import re
from pathlib import Path

SERVICE_PATH = Path(__file__).parent / "app" / "rag_service.py"
TREE = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))

NAMES = {
    "_STOP_WORDS", "_PHRASES", "_tokens", "_sentences",
    "_question_kind", "_requested_phrases", "_requested_concepts",
    "_extract_raw_context", "_select_extractive_answer",
}
nodes = []
for node in TREE.body:
    assigned = set()
    if isinstance(node, ast.FunctionDef):
        assigned.add(node.name)
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned.add(target.id)
    if assigned & NAMES:
        nodes.append(node)

namespace = {"re": re}
module = ast.Module(body=nodes, type_ignores=[])
exec(compile(module, str(SERVICE_PATH), "exec"), namespace)

context = """Python is a programming language.

Python supports variables, functions, loops and conditions.

Python is widely used in Artificial Intelligence,
Machine Learning, Data Science and Web Development.

Python supports Object Oriented Programming."""

chunks = [{"content": context, "filename": "python_notes.txt", "chunk_number": 1}]
cases = [
    ("What is Python?", "Python is a programming language."),
    ("Which basic programming concepts does Python support?",
     "Python supports variables, functions, loops and conditions."),
    ("In which areas is Python widely used?",
     "Python is widely used in Artificial Intelligence, Machine Learning, Data Science and Web Development."),
    ("Does Python support Object Oriented Programming?",
     "Yes. Python supports Object Oriented Programming."),
    ("Does the knowledge document mention Python variables and functions?",
     "Yes. The document mentions Functions and Variables."),
]

failed = 0
for question, expected in cases:
    actual = namespace["_select_extractive_answer"](question, chunks)
    ok = actual == expected
    print(f"{'PASS' if ok else 'FAIL'}: {question}")
    if not ok:
        print("  Expected:", expected)
        print("  Actual:  ", actual)
        failed += 1

print(f"\nRegression tests: {len(cases) - failed}/{len(cases)} passed")
raise SystemExit(1 if failed else 0)