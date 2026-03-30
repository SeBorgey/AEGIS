from typing import Optional
from pathlib import Path
import json

from core.llm_client import LLMClient
from core.log_manager import LogManager
from action_api import ActionExecutor, ActionCall, ActionResult, AgentResponse


class ManagerAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        executor: ActionExecutor,
        log_manager: LogManager,
        max_iterations: int = 50,
        dataset_collector=None,
        tool_suggest_client=None,
        top_k: int = 3,
    ):
        self.llm = llm_client
        self.executor = executor
        self.log = log_manager
        self.max_iterations = max_iterations
        self.messages = []
        self.agent_name = "manager"
        self.dataset_collector = dataset_collector
        self.tool_suggest_client = tool_suggest_client
        self.top_k = top_k
        self.step_count = 0

    def _build_system_prompt(self, tools_section: str | None = None, dynamic_tools: bool = False) -> str:
        if tools_section is None:
            if dynamic_tools:
                tools_section = "Available tools are provided at the end of the context for each step."
            else:
                tools_section = """- run_coder: {"instruction": "text"} - Send instructions to the Coder Agent. First call should include the RPD. Subsequent calls should include feedback or new tasks.
- finish_work: {} - Call this ONLY when the project is fully completed and verified. This will trigger the final build.
- get_project_tree: {} - Get the file structure of the project.
- get_all_symbols: {"file_path": "path/to/file.py"} - Get a list of classes and functions in a file with line numbers.
- open_file: {"file_path": "path/to/file.py", "start_line": 1, "end_line": 100} - Read file content. Parameters start_line and end_line are optional - use them to read only specific lines (e.g., start_line: 10, end_line: 50). If omitted, reads entire file.
- terminal_command: {"cmd": ["command", "args"]} - Run a terminal command (use sparingly, e.g., for grep)."""
        return f"""You are a Project Manager Agent. Your goal is to oversee the development of a software project.
This project must be a Python program with GUI (PySide6).
You manage a Coder Agent who writes the code. For installing libraries `uv pip install`.

Process:
1. Analyze the user's request.
2. Create a Rapid Product Development (RPD) document and send it to the Coder Agent.
3. Create a development checklist based on the RPD.
5. Review the Coder's work using your tools and checklist.
6. If there are issues, instruct the Coder to fix them.
7. Repeat steps 5-6 until the project is complete and correct.
8. Finish the work.

Available Tools:
{tools_section}

Important:
- Don't divide a project into phases. The project should be developed from the first call to the Coder. Your goal is to check if they forgot anything.
- Use get_all_symbols + open_file with start_line and end_line to look at specific implementations and not clutter up your context.
- Main file MUST be named app.py (entry point)
- requirements.txt do not needed.
"""

    def _get_tools_section(self) -> str | None:
        if self.tool_suggest_client is None:
            return None
        from tool_suggest_experiment.tool_filter import get_suggested_tools_section, MANAGER_TOOLS, MANAGER_TERMINAL_TOOLS
        return get_suggested_tools_section(
            self.tool_suggest_client, self.messages, MANAGER_TOOLS, self.top_k,
            terminal_tools=MANAGER_TERMINAL_TOOLS,
        )

    def run(self, user_request: str) -> bool:
        self.log.start_chat(self.agent_name)

        if self.tool_suggest_client:
            system_prompt = self._build_system_prompt(dynamic_tools=True)
        else:
            system_prompt = self._build_system_prompt()

        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Request: {user_request}"},
        ]

        self.log.append_chat("system", system_prompt, self.agent_name)
        self.log.append_chat("user", user_request, self.agent_name)

        finish_work_attempts = 0

        for iteration in range(self.max_iterations):
            self.log.info(f"Manager Iteration {iteration + 1}/{self.max_iterations}")
            self.step_count += 1

            messages_to_send = self.messages
            if self.tool_suggest_client:
                tools_section = self._get_tools_section()
                if tools_section:
                    self.log.append_chat("system", tools_section, self.agent_name)
                    messages_to_send = [msg.copy() for msg in self.messages]
                    messages_to_send[-1]["content"] += tools_section
            
            response = self.llm.chat(messages_to_send, response_model=AgentResponse)
            if not response:
                self.log.error("Empty LLM response for Manager")
                return False

            response_dict = response.model_dump() if hasattr(response, "model_dump") else response.dict()
            response_json = json.dumps(response_dict, ensure_ascii=False, indent=2)

            self.log.append_chat("assistant", f"```json\n{response_json}\n```", self.agent_name)
            self.messages.append({"role": "assistant", "content": response_json})

            thought = response.thought
            action_name = response.action
            params = response.params.model_dump(exclude_none=True) if hasattr(response.params, "model_dump") else response.params

            self.log.info(f"Manager Thought: {thought}")
            self.log.info(f"Manager Action: {action_name}({params})")

            if self.dataset_collector and action_name:
                try:
                    self.dataset_collector.record_step(self.messages, action_name)
                except Exception as e:
                    self.log.warning(f"Failed to record step for tool-suggest: {e}")

            call = ActionCall(name=action_name, params=params)
            result = self.executor.execute(call)

            result_text = self._format_result(result)
            self.log.append_chat("system", result_text, self.agent_name)
            self.messages.append({"role": "user", "content": result_text})

            if action_name == "finish_work":
                if result.success:
                    return True
                else:
                    finish_work_attempts += 1
                    if finish_work_attempts >= 5:
                        self.log.error(f"Failed to finish work after {finish_work_attempts} attempts. Aborting.")
                        self.messages.append({"role": "user", "content": f"System error: Failed to finish work after 5 attempts. The build process is broken. Stop trying and return an error."})
                        return False

        self.log.error("Manager max iterations reached")
        return False

    def _format_result(self, result: ActionResult) -> str:
        if result.success:
            data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
            return f"Success:\n{data_str}"
        return f"Error: {result.error}"
