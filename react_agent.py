import json
import re
from typing import Optional

from action_api import ActionCall, ActionExecutor, ActionResult, AgentResponse
from code_executor import CodeExecutor
from llm_client import LLMClient
from log_manager import LogManager


class ReActAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        executor: ActionExecutor,
        code_executor: CodeExecutor,
        log_manager: LogManager,
        max_iterations: int = 30,
        agent_name: str = "coder",
    ):
        self.llm = llm_client
        self.executor = executor
        self.code_executor = code_executor
        self.log = log_manager
        self.max_iterations = max_iterations
        self.agent_name = agent_name
        self.messages = []

    def _build_system_prompt(self) -> str:
        return """You are an autonomous programmer agent. You create Python programs with GUI (PySide6).

Available actions:
- read_file: {"path": "file.py"}
- create_file: {"path": "file.py", "content": "code"}
- edit_file: {"path": "file.py", "old": "old text", "new": "new text"}
- get_file_tree: {"start_path": ".", "max_depth": 2} - show file structure
- run_command: {"cmd": ["command", "args"]} - any terminal command
- run_ipython: {"code": "print('hello')"} - execute python code in interactive environment (state is preserved)
- finish_task: {} - finish task execution and run tests



Requirements:
- Main file MUST be named app.py (entry point)
- You can create any project structure, as many files as needed
- Use PySide6 for GUI
- Main file app.py must contain if __name__ == "__main__": and application launch
- Only one "action" field per message.

Important:
- DO NOT launch the application manually via run_command
- When finished, call finish_task - the application will be tested automatically
- If the test fails - you will receive an error and can fix it
- Install libraries (pip install) only if you receive an error about their absence
- Do not install libraries preventively
- Do not use placeholders TODO and others, write all the code at once.
- ALWAYS set accessibleName for buttons or interactive widgets that do not contain visible text (e.g., icon-only buttons) so the automated tester can find and click them.
- DO NOT write placeholders for API keys in the code (e.g. `API_KEY = "your_key_here"`). If your application requires an API key, the GUI MUST ask the user to input it (e.g. via an input dialog or text field)."""

    def run(self, task: str) -> bool:
        self.log.start_chat(self.agent_name)

        if not self.messages:
            system_prompt = self._build_system_prompt()
            self.messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Task: {task}"},
            ]
            self.log.append_chat("system", system_prompt, self.agent_name)
            self.log.append_chat("user", task, self.agent_name)
        else:
            self.messages.append({"role": "user", "content": task})
            self.log.append_chat("user", task, self.agent_name)

        for iteration in range(self.max_iterations):
            self.log.info(f"Iteration {iteration + 1}/{self.max_iterations}")

            response = self.llm.chat(self.messages, response_model=AgentResponse)
            if not response:
                self.log.error("Empty LLM response")
                return False

            response_dict = response.model_dump() if hasattr(response, "model_dump") else response.dict()
            response_json = json.dumps(response_dict, ensure_ascii=False, indent=2)
            self.log.append_chat("assistant", f"```json\n{response_json}\n```", self.agent_name)
            self.messages.append({"role": "assistant", "content": response_json})

            thought = response.thought
            action_name = response.action
            params = response.params

            if not action_name:
                if params.get("done"):
                     action_name = "finish_task"
                else:
                    self.log.warning("No action")
                    self.messages.append({"role": "user", "content": "Specify action"})
                    continue

            self.log.info(f"Thought: {thought}")
            self.log.info(f"Action: {action_name}({params})")

            if action_name == "finish_task":
                self.log.info("Agent says finish_task, testing app...")
                test_success, test_message = self.code_executor.test_app("app.py")

                if test_success:
                    self.log.info("Test passed")
                    return True

                self.log.warning(f"Test failed: {test_message}")
                self.log.append_chat("system", f"Test failed:\n{test_message}", self.agent_name)
                self.messages.append(
                    {
                        "role": "user",
                        "content": f"Application failed. Error:\n{test_message}\n\nFix it.",
                    }
                )
                continue
            
            call = ActionCall(name=action_name, params=params)
            result = self.executor.execute(call)

            result_text = self._format_result(result)
            self.log.append_chat("system", result_text, self.agent_name)
            self.messages.append({"role": "user", "content": result_text})

            if not result.success:
                self.log.warning(f"Failed: {result.error}")

        self.log.error("Max iterations reached")
        return False

    def _format_result(self, result: ActionResult) -> str:
        if result.success:
            data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
            return f"Success:\n{data_str}"
        return f"Error: {result.error}"
