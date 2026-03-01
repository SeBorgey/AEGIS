import base64
import csv
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, Union

from app_tester import AppTester
from llm_client import LLMClient
from log_manager import LogManager
from action_api import AgentResponse


class JudgeAgent:
    def __init__(
        self,
        run_path: str,
        llm_client: LLMClient,
        log_manager: LogManager,
        max_iterations: int = 200,
    ):
        self.run_path = Path(run_path).resolve()
        self.llm = llm_client
        self.log = log_manager
        self.max_iterations = max_iterations
        self.tester = AppTester()
        self.messages = []
        self.agent_name = "judge"

    def _get_original_task(self) -> str:
        task_file = self.run_path / "logs" / "metadata" / "original_task"
        if task_file.exists():
            return task_file.read_text(encoding="utf-8").strip()
        
        metadata_file = self.run_path / "logs" / "metadata.json"
        if metadata_file.exists():
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
                return data.get("original_task", "")
            except Exception:
                pass
        
        return ""

    def _build_system_prompt(self, task: str) -> str:
        return f"""You are an expert QA Judge. Your goal is to evaluate a GUI application based on the user's requirements.

User Task: "{task}"

You have access to the application executable in the 'code/dist' folder.
You must:
1. Launch the application.
2. Explore the interface (click buttons, type text).
3. Verify if the application fulfills the user's task.
4. Give a score (1-10) and a comment.

Available Tools:
- start: {{}} - Launch the app. Returns a screenshot and list of available widgets.
- click: {{"widget_name": "Button Name"}} - Click a widget by its name. Returns a screenshot and list of available widgets.
- right_click: {{"widget_name": "Button Name"}} - Right click a widget by its name. Returns a screenshot and list of available widgets.
- type_text: {{"text": "hello", "widget_name": "Field Name"}} - Type text. 'widget_name' is optional, but highly recommended to click before typing. Returns a screenshot and list of available widgets.
- run_command: {{"cmd": ["ls", "-la"]}} - Run a terminal command.
- finish: {{"score": 8, "comment": "Good app but missing X"}} - Finish evaluation.

CRITICAL RULE:
- YOU ARE STRICTLY FORBIDDEN from reading source code (e.g., .py files). Your ONLY job is black-box testing. You can check side effects (databases, generated files) via run_command, but do NOT read the code to verify logic.

Notes:
- You will receive screenshots and a list of available interactive widgets after `start`, `click`, and `type_text`.
- Use the widget names from the list to click on them.
- Analyze the screenshots to decide what to do next.
- Be critical but fair.
- In response to this message, write a test plan and run the application.
"""

    def _find_executable(self) -> str:
        app_path = self.run_path / "code" / "dist" / "app"
        if app_path.exists() and os.access(app_path, os.X_OK):
            return str(app_path)
        return ""

    def run(self):
        self.log.start_chat(self.agent_name)
        task = self._get_original_task()
        if not task:
            self.log.error("Could not find original task")
            return

        system_prompt = self._build_system_prompt(task)
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start evaluation."},
        ]
        self.log.append_chat("system", system_prompt, self.agent_name)
        self.log.append_chat("user", "Start evaluation.", self.agent_name)

        exe_path = self._find_executable()
        if exe_path:
            self.log.info(f"Found executable: {exe_path}")
            self.messages.append({"role": "user", "content": f"Hint: Executable found at {exe_path}"})

        try:
            for iteration in range(self.max_iterations):
                self.log.info(f"Iteration {iteration + 1}/{self.max_iterations}")
                
                response = self.llm.chat(self.messages, response_model=AgentResponse)
                if not response:
                    self.log.error("Empty LLM response")
                    break

                response_dict = response.model_dump() if hasattr(response, "model_dump") else response.dict()
                response_json = json.dumps(response_dict, ensure_ascii=False, indent=2)

                self.log.append_chat("assistant", f"```json\n{response_json}\n```", self.agent_name)
                self.messages.append({"role": "assistant", "content": response_json})

                thought = response.thought
                action = response.action
                params = response.params

                self.log.info(f"Thought: {thought}")
                self.log.info(f"Action: {action}({params})")

                if action == "finish":
                    score = params.get("score")
                    comment = params.get("comment")
                    self.log.info(f"Judge finished. Score: {score}, Comment: {comment}")
                    self._save_result(task, score, comment)
                    return

                result_text, image_path = self._execute_tool(action, params, iteration)
                
                if not result_text.startswith("!["): # If not an image link (which is already logged)
                     self.log.append_chat("system", result_text, self.agent_name)
                
                if image_path:
                    try:
                        with open(image_path, "rb") as img_file:
                            b64_image = base64.b64encode(img_file.read()).decode("utf-8")
                        
                        message_content = [
                            {"type": "text", "text": result_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                            },
                        ]
                        self.messages.append({"role": "user", "content": message_content})
                    except Exception as e:
                        self.log.error(f"Failed to encode image: {e}")
                        self.messages.append({"role": "user", "content": result_text})
                else:
                    self.messages.append({"role": "user", "content": result_text})

        finally:
            self.tester.stop()

    def _save_result(self, task: str, score, comment: str):
        csv_path = Path("runs") / "judge_results.csv"
        file_exists = csv_path.exists()
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            if not file_exists:
                writer.writerow(["run", "task", "score", "comment"])
            writer.writerow([self.run_path.name, task, score, comment])

    def _execute_tool(self, action: str, params: dict, iteration: int) -> Tuple[str, Optional[str]]:
        try:
            if action == "start":
                app_path = self._find_executable()
                if not app_path:
                    return "Error: Could not find executable at code/dist/app", None
                self.tester.launch(app_path)
                return self._capture_and_log_screenshot(f"step_{iteration}_start")

            elif action == "click":
                widget_name = params.get("widget_name")
                if not widget_name:
                    return "Error: widget_name required", None
                self.tester.click(widget_name)
                return self._capture_and_log_screenshot(f"step_{iteration}_click")

            elif action == "right_click":
                widget_name = params.get("widget_name")
                if not widget_name:
                    return "Error: widget_name required", None
                self.tester.right_click(widget_name)
                return self._capture_and_log_screenshot(f"step_{iteration}_right_click")

            elif action == "type_text":
                text = params.get("text")
                widget_name = params.get("widget_name")
                if not text:
                    return "Error: text required", None
                if widget_name:
                    try:
                        self.tester.click(widget_name)
                        time.sleep(0.5)
                    except ValueError:
                        return f"Error: Widget '{widget_name}' not found", None
                self.tester.type_text(text)
                return self._capture_and_log_screenshot(f"step_{iteration}_type")

            elif action == "run_command":
                cmd = params.get("cmd")
                if not cmd:
                    return "Error: cmd required", None
                result = subprocess.run(
                    cmd, capture_output=True, text=True, cwd=str(self.run_path)
                )
                return f"Stdout:\n{result.stdout}\nStderr:\n{result.stderr}", None

            else:
                return f"Unknown tool: {action}", None

        except Exception as e:
            return f"Tool execution error: {str(e)}", None

    def _capture_and_log_screenshot(self, name: str) -> Tuple[str, str]:
        filename = f"{name}.png"
        save_path = self.log.logs_dir / filename
        self.tester.screenshot(str(save_path))
        
        widget_names = self.tester.get_element_names()
        widgets_text = "\n\nAvailable widgets: " + ", ".join(widget_names) if widget_names else "\n\nNo interactive widgets found."
        
        # Log image to chat
        self.log.append_image(filename, caption=name, role="system", session_name=self.agent_name)
        
        return f"Screenshot captured: ![{name}]({filename}){widgets_text}", str(save_path)
