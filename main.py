import os
import json
from pathlib import Path

from llm_client import LLMClient
from react_agent import ReActAgent
from code_executor import CodeExecutor
from log_manager import LogManager
from action_api import ActionPolicy, PolicyConfig, ActionExecutor, build_registry


def run_task(task_description: str, workspace: str, log_manager: LogManager) -> bool:
    workspace_path = Path(workspace).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        log_manager.error("OPENAI_API_KEY not found")
        return False

    policy_config = PolicyConfig(
        root_dir=workspace_path,
        allowed_commands=["python", "pip"],
        command_timeout_sec=30,
        max_read_bytes=1048576,
        max_write_bytes=1048576,
        allow_shell=False,
        max_output_chars=500000,
    )

    policy = ActionPolicy(policy_config)
    registry = build_registry(policy)
    executor = ActionExecutor(policy, registry)

    llm_client = LLMClient(api_key=api_key)
    agent = ReActAgent(
        llm_client=llm_client,
        executor=executor,
        log_manager=log_manager,
        max_iterations=50,
    )

    log_manager.info(f"Task: {task_description}")
    success = agent.run(task_description)

    if not success:
        log_manager.error("Agent failed")
        return False

    log_manager.info("Agent completed, packaging...")
    code_executor = CodeExecutor(str(workspace_path))
    pack_success, pack_message = code_executor.package_to_exe("app.py")

    if pack_success:
        log_manager.info(pack_message)
    else:
        log_manager.error(pack_message)

    return pack_success


def main():
    log_manager = LogManager(base_dir="logs", retention_days=7)

    dataset_path = Path("datassets/middle.json")

    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task_item in tasks:
            workspace = Path("workspaces") / task_item.replace(" ", "_")
            task = f"Создай программу: {task_item}"

            log_manager.info(f"\n{'='*60}\n{task_item}\n{'='*60}")
            run_task(task, str(workspace), log_manager)
    else:
        task = "Создай калькулятор с GUI на PySide6"
        run_task(task, "workspaces/calculator", log_manager)


if __name__ == "__main__":
    main()