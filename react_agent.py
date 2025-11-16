import json
import re
from typing import Optional
from action_api import ActionCall, ActionResult, ActionExecutor
from llm_client import LLMClient
from log_manager import LogManager


class ReActAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        executor: ActionExecutor,
        log_manager: LogManager,
        max_iterations: int = 30,
    ):
        self.llm = llm_client
        self.executor = executor
        self.log = log_manager
        self.max_iterations = max_iterations
        self.messages = []

    def _build_system_prompt(self) -> str:
        return """Ты автономный агент-программист. Создаёшь программы на Python с GUI (PySide6).

Доступные действия:
- read_file: {"path": "file.py"}
- create_file: {"path": "file.py", "content": "код"}
- edit_file: {"path": "file.py", "old": "старый текст", "new": "новый текст"}
- run_command: {"cmd": ["python", "script.py"], "env": {"VAR": "value"}}

Для тестирования PySide6 используй: {"cmd": ["python", "app.py"], "env": {"QT_QPA_PLATFORM": "offscreen"}}

Формат ответа (только JSON в ```json блоке):
1. Выполнить действие:
```json
{
  "thought": "что делаю и зачем",
  "action": "имя_действия",
  "params": {...}
}
``` {data-source-line="48"}

2. Завершить:
```json
{
  "thought": "итоги работы",
  "done": true
}
``` {data-source-line="56"}

Требования:
- Основной файл называй app.py
- Используй только PySide6 для GUI
- Не пиши комментарии
- Тестируй перед завершением
- Исправляй ошибки если появляются
- Весь код в одном файле"""

    def _parse_response(self, text: str) -> Optional[dict]:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None

    def run(self, task: str) -> bool:
        self.log.start_chat("react")

        system_prompt = self._build_system_prompt()
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Задача: {task}"},
        ]

        self.log.append_chat("system", system_prompt)
        self.log.append_chat("user", task)

        for iteration in range(self.max_iterations):
            self.log.info(f"Iteration {iteration + 1}/{self.max_iterations}")

            response = self.llm.chat(self.messages)
            if not response:
                self.log.error("Empty LLM response")
                return False

            self.log.append_chat("assistant", response)
            self.messages.append({"role": "assistant", "content": response})

            parsed = self._parse_response(response)
            if not parsed:
                self.log.warning("Failed to parse response")
                self.messages.append(
                    {"role": "user", "content": "Используй JSON формат в ```json блоке"}
                )
                continue

            if parsed.get("done"):
                self.log.info("Task completed")
                return True

            thought = parsed.get("thought", "")
            action_name = parsed.get("action")
            params = parsed.get("params", {})

            if not action_name:
                self.log.warning("No action")
                self.messages.append({"role": "user", "content": "Укажи action"})
                continue

            self.log.info(f"Thought: {thought}")
            self.log.info(f"Action: {action_name}({params})")

            call = ActionCall(name=action_name, params=params)
            result = self.executor.execute(call)

            result_text = self._format_result(result)
            self.log.append_chat("system", result_text)
            self.messages.append({"role": "user", "content": result_text})

            if not result.success:
                self.log.warning(f"Failed: {result.error}")

        self.log.error("Max iterations reached")
        return False

    def _format_result(self, result: ActionResult) -> str:
        if result.success:
            data_str = json.dumps(result.data, ensure_ascii=False, indent=2)
            return f"Успех:\n{data_str}"
        return f"Ошибка: {result.error}"