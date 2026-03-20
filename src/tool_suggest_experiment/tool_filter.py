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
    "run_coder": '{"instruction": "text"} - Send instructions to the Coder Agent.',
    "finish_work": "{} - Call this ONLY when the project is fully completed and verified.",
    "get_project_tree": "{} - Get the file structure of the project.",
    "get_all_symbols": '{"file_path": "path/to/file.py"} - Get a list of classes and functions in a file with line numbers.',
    "open_file": '{"file_path": "path/to/file.py", "start_line": 1, "end_line": 100} - Read file content.',
    "terminal_command": '{"cmd": ["command", "args"]} - Run a terminal command.',
}


def get_suggested_tools_section(
    client: ToolSuggestClient,
    messages: list[dict],
    all_tools: dict[str, str],
    top_k: int = 3,
) -> str:
    if not client.is_trained:
        return _format_tools(all_tools)

    context = openai_messages_to_pydantic(messages)
    suggestions = asyncio.get_event_loop().run_until_complete(
        client.suggest(context, top_k=top_k)
    )
    suggested_names = {s.id for s in suggestions}

    filtered = {k: v for k, v in all_tools.items() if k in suggested_names}
    if not filtered:
        return _format_tools(all_tools)
    return _format_tools(filtered)


def _format_tools(tools: dict[str, str]) -> str:
    lines = []
    for name, desc in tools.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)
