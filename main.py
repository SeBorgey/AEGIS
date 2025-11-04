import json
import os

from agent import ProgrammingAgent
from code_executor import CodeExecutor
from llm_client import LLMClient


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Ошибка: не найдена переменная окружения OPENAI_API_KEY.")
        print("Пожалуйста, запустите скрипт через './run.sh'")
        return

    #     task = """
    # Напиши мне простой браузер
    # """

    #     print("Инициализация компонентов...")
    #     llm_client = LLMClient(api_key=api_key)
    #     code_executor = CodeExecutor(workspace_path="project_files")
    #     agent = ProgrammingAgent(llm_client, code_executor)

    #     agent.create_program(task)

    with open("datasets/middle.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)

    for task_item in tasks:
        task = f"Напиши мне {task_item}"

        print("Инициализация компонентов...")
        llm_client = LLMClient(api_key=api_key)
        code_executor = CodeExecutor(workspace_path=task_item)
        agent = ProgrammingAgent(llm_client, code_executor)

        agent.create_program(task)


if __name__ == "__main__":
    main()
