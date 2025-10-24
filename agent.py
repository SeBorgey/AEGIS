from code_executor import CodeExecutor
from llm_client import LLMClient


class ProgrammingAgent:
    def __init__(self, llm_client: LLMClient, code_executor: CodeExecutor):
        self.llm_client = llm_client
        self.code_executor = code_executor

    def _create_initial_prompt(self, task_description: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": """Задание: Напиши код программы на Python с использованием GUI-библиотеки PySide6.

Требования:
1.  Весь код должен находиться в одном файле.
2.  Приложение должно быть полностью самодостаточным.
3.  Код не должен содержать комментариев.
4.  Ответ должен содержать только код в блоке ```python ... ```.
5.  Точка входа в приложение должна быть определена через `if __name__ == "__main__":`.
""",
            },
            {"role": "user", "content": task_description},
        ]

    def _create_fix_prompt(self, code: str, error_message: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": """Задание: Исправь ошибку в предоставленном коде.

Требования:
1.  Полностью перепиши код с исправлением.
2.  Используй GUI-библиотеку PySide6.
3.  Весь код должен находиться в одном файле.
4.  Не добавляй в код комментарии или объяснения.
5.  Ответ должен содержать только исправленный код в блоке ```python ... ```.
""",
            },
            {
                "role": "user",
                "content": f"""
Вот код, который нужно исправить:
```python
{code}
```

Вот ошибка, которую он выдает при запуске:
```
{error_message}
```

Пожалуйста, перепиши код полностью, чтобы он работал.
""",
            },
        ]

    def create_program(self, task_description: str, max_retries: int = 5):
        print("Начинаю работу над задачей...")
        messages = self._create_initial_prompt(task_description)

        for i in range(max_retries):
            print(f"\n--- Попытка {i + 1} из {max_retries} ---")
            print("1. Генерирую код...")
            code = self.llm_client.generate_code(messages)

            if not code:
                print("Не удалось сгенерировать код. Прерываю работу.")
                return

            script_path = self.code_executor.save_code(code)

            print(f"2. Код сохранен в '{script_path}'. Запускаю headless-тест...")
            success, output = self.code_executor.run_headless_test(script_path)

            if success:
                print("3. Тест успешно пройден! Код рабочий.")
                print("4. Начинаю упаковку в .exe файл...")
                pack_success, pack_output = self.code_executor.package_with_pyinstaller(
                    script_path
                )

                if pack_success:
                    print("\n--- УСПЕХ! ---")
                    print(pack_output)
                else:
                    print("\n--- ОШИБКА УПАКОВКИ ---")
                    print(pack_output)
                return

            print(f"3. Тест провален. Ошибка:\n{output}")
            messages = self._create_fix_prompt(code, output)

        print("\n--- ПРОВАЛ ---")
        print(f"Не удалось получить рабочий код за {max_retries} попыток.")
