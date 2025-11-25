from typing import Optional
from pathlib import Path
import json

from llm_client import LLMClient
from log_manager import LogManager
from action_api import ActionExecutor, ActionCall, ActionResult


class ManagerAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        executor: ActionExecutor,
        log_manager: LogManager,
        max_iterations: int = 50,
    ):
        self.llm = llm_client
        self.executor = executor
        self.log = log_manager
        self.max_iterations = max_iterations
        self.messages = []
        self.agent_name = "manager"

    def _build_system_prompt(self) -> str:
        return """You are a Project Manager Agent. Your goal is to oversee the development of a software project.
This project myst be a Python program with GUI (PySide6).
You manage a Coder Agent who writes the code. 

Process:
1. Analyze the user's request.
2. Create a Rapid Product Development (RPD) document and send it to the Coder Agent.
Don't divide a project into phases. The project should be developed from the first call to the Coder. 
Your goal is to check if they forgot anything.
3. Create a development checklist based on the RPD.
5. Review the Coder's work using your tools and checklist.
6. If there are issues, instruct the Coder to fix them.
7. Repeat steps 5-6 until the project is complete and correct.
8. Finish the work.

Available Tools:
- run_coder: {"instruction": "text"} - Send instructions to the Coder Agent. First call should include the RPD. Subsequent calls should include feedback or new tasks.
- finish_work: {} - Call this ONLY when the project is fully completed and verified. This will trigger the final build.
- get_project_tree: {} - Get the file structure of the project.
- get_all_symbols: {"file_path": "path/to/file.py"} - Get a list of classes and functions in a file with line numbers.
- open_file: {"file_path": "path/to/file.py", "start_line": 1, "end_line": 100} - Read the content of a file.
- terminal_command: {"cmd": ["command", "args"]} - Run a terminal command (use sparingly, e.g., for grep).

Response format (only JSON in ```json block):
```json
{
  "thought": "reasoning",
  "action": "tool_name",
  "params": {...}
}
```
"""

    def _parse_response(self, text: str) -> Optional[dict]:
        import re
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def run(self, user_request: str) -> bool:
        self.log.start_chat(self.agent_name)
        
        system_prompt = self._build_system_prompt()
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Request: {user_request}"},
        ]
        
        self.log.append_chat("system", system_prompt, self.agent_name)
        self.log.append_chat("user", user_request, self.agent_name)

        for iteration in range(self.max_iterations):
            self.log.info(f"Manager Iteration {iteration + 1}/{self.max_iterations}")
            
            response = self.llm.chat(self.messages)
            if not response:
                self.log.error("Empty LLM response for Manager")
                return False

            self.log.append_chat("assistant", response, self.agent_name)
            self.messages.append({"role": "assistant", "content": response})

            parsed = self._parse_response(response)
            if not parsed:
                self.log.warning("Failed to parse Manager response")
                self.messages.append(
                    {"role": "user", "content": "Use JSON format in ```json block"}
                )
                continue

            thought = parsed.get("thought", "")
            action_name = parsed.get("action")
            params = parsed.get("params", {})

            self.log.info(f"Manager Thought: {thought}")
            self.log.info(f"Manager Action: {action_name}({params})")

            call = ActionCall(name=action_name, params=params)
            result = self.executor.execute(call)

            result_text = self._format_result(result)
            self.log.append_chat("system", result_text, self.agent_name)
            self.messages.append({"role": "user", "content": result_text})

            if action_name == "finish_work" and result.success:
                return True

        self.log.error("Manager max iterations reached")
        return False

    def _format_result(self, result: ActionResult) -> str:
        if result.success:
            data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
            return f"Success:\n{data_str}"
        return f"Error: {result.error}"
