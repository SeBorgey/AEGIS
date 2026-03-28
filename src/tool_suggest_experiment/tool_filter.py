import asyncio
from tool_suggest.client import ToolSuggestClient
from tool_suggest_experiment.message_converter import openai_messages_to_pydantic


CODER_TOOLS = {
    "read_file": '{"path": "file.py"}',
    "create_file": '{"path": "file.py", "content": "code"}',
    "edit_file": '{"path": "file.py", "old": "old text", "new": "new text"}',
    "get_file_tree": '{"start_path": ".", "max_depth": 2} - show file structure',
    "run_command": '{"cmd": ["command", "args"]} - any terminal command',
    "run_ipython": '{"code": "print(\'hello\')"} - execute python code in interactive environment (state is preserved)',
    "finish_task": "{} - finish task execution and run tests",
}

MANAGER_TOOLS = {
    "run_coder": '{"instruction": "text"} - Send instructions to the Coder Agent. First call should include the RPD. Subsequent calls should include feedback or new tasks.',
    "finish_work": "{} - Call this ONLY when the project is fully completed and verified. This will trigger the final build.",
    "get_project_tree": "{} - Get the file structure of the project.",
    "get_all_symbols": '{"file_path": "path/to/file.py"} - Get a list of classes and functions in a file with line numbers.',
    "open_file": '{"file_path": "path/to/file.py", "start_line": 1, "end_line": 100} - Read file content. Parameters start_line and end_line are optional - use them to read only specific lines (e.g., start_line: 10, end_line: 50). If omitted, reads entire file.',
    "terminal_command": '{"cmd": ["command", "args"]} - Run a terminal command (use sparingly, e.g., for grep).',
}

CODER_TERMINAL_TOOLS = {"finish_task"}
MANAGER_TERMINAL_TOOLS = {"finish_work"}


def get_suggested_tools_section(
    client: ToolSuggestClient,
    messages: list[dict],
    all_tools: dict[str, str],
    top_k: int = 3,
    terminal_tools: set[str] | None = None,
) -> str:
    if not client.is_trained:
        return _format_tools(all_tools)

    context = openai_messages_to_pydantic(messages)
    suggestions = asyncio.run(
        client.suggest(context, top_k=top_k)
    )
    suggested_names = {s.id for s in suggestions}

    if terminal_tools:
        suggested_names |= terminal_tools

    filtered = {k: v for k, v in all_tools.items() if k in suggested_names}
    if not filtered:
        return f"\n\n### Available Tools for this step:\n" + _format_tools(all_tools)
    return f"\n\n### Available Tools for this step:\n" + _format_tools(filtered)


def _format_tools(tools: dict[str, str]) -> str:
    lines = []
    for name, desc in tools.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)
