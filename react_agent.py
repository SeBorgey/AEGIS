import json
import re
from typing import Optional

from action_api import ActionCall, ActionExecutor, ActionResult
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
    ):
        self.llm = llm_client
        self.executor = executor
        self.code_executor = code_executor
        self.log = log_manager
        self.max_iterations = max_iterations
        self.messages = []

    def _build_system_prompt(self) -> str:
        return """Ты автономный агент-программист. Создаёшь программы на Python с GUI (PySide6).

Доступные действия:
- read_file: {"path": "file.py"}
- create_file: {"path": "file.py", "content": "код"}
- edit_file: {"path": "file.py", "old": "старый текст", "new": "новый текст"}
- get_file_tree: {"start_path": ".", "max_depth": 2} - показать структуру файлов
- run_command: {"cmd": ["команда", "аргументы"]} - любая терминальная команда
- run_ipython: {"code": "print('hello')"} - выполнить python код в интерактивной среде (состояние сохраняется)
- finish_task: {} - завершить выполнение задачи и запустить тесты

Формат ответа (только JSON в ```json блоке):
```json
{
  "thought": "что делаю и зачем",
  "action": "имя_действия",
  "params": {...}
}
```

Требования:
- Главный файл ОБЯЗАТЕЛЬНО называй app.py (точка входа)
- Можешь создавать любую структуру проекта, сколько угодно файлов
- Используй PySide6 для GUI
- Главный файл app.py должен содержать if __name__ == "__main__": и запуск приложения
- В одном сообщении может быть только одно поле "action".

Важно:
- НЕ запускай приложение вручную через run_command
- Когда закончишь, вызови finish_task - приложение автоматически протестируется
- Если тест провалится - получишь ошибку и сможешь исправить
- Устанавливай библиотеки (pip install) только если получил ошибку о их отсутствии
- Не устанавливай библиотеки превентивно"""

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

            thought = parsed.get("thought", "")
            action_name = parsed.get("action")
            params = parsed.get("params", {})

            if not action_name:
                if parsed.get("done"):
                     action_name = "finish_task"
                else:
                    self.log.warning("No action")
                    self.messages.append({"role": "user", "content": "Укажи action"})
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
                self.log.append_chat("system", f"Тест провален:\n{test_message}")
                self.messages.append(
                    {
                        "role": "user",
                        "content": f"Приложение не работает. Ошибка:\n{test_message}\n\nИсправь.",
                    }
                )
                continue
            
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
