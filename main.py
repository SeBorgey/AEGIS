import os
import json
from pathlib import Path

from llm_client import LLMClient
from react_agent import ReActAgent
from manager_agent import ManagerAgent
from code_executor import CodeExecutor
from log_manager import LogManager
from action_api import ActionPolicy, PolicyConfig, ActionExecutor, build_registry, build_manager_registry


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
    code_executor = CodeExecutor(str(workspace_path))

    llm_client = LLMClient(api_key=api_key)
    
    coder_agent = ReActAgent(
        llm_client=llm_client,
        executor=executor,
        code_executor=code_executor,
        log_manager=log_manager,
        max_iterations=500,
        agent_name="coder"
    )

    manager_registry = build_manager_registry(policy, coder_agent, code_executor)
    manager_executor = ActionExecutor(policy, manager_registry)

    manager_agent = ManagerAgent(
        llm_client=llm_client,
        executor=manager_executor,
        log_manager=log_manager,
        max_iterations=300
    )

    log_manager.info(f"Task: {task_description}")
    log_manager.save_metadata({"original_task": task_description})
    
    success = manager_agent.run(task_description)

    if not success:
        log_manager.error("Manager Agent failed")
        return False

    log_manager.info("Manager Agent completed successfully.")
    return True


def main():
    log_manager = LogManager(base_dir="logs", retention_days=7)

    # dataset_path = Path("datasets/middle.json")
    dataset_path = Path("non_existent_file.json")

    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task_item in tasks:
            workspace = Path("workspaces") / task_item.replace(" ", "_")
            task = f"Create program: {task_item}"

            log_manager.info(f"\n{'='*60}\n{task_item}\n{'='*60}")
            run_task(task, str(workspace), log_manager)
    else:
        task = "Write me a calculator - a calculator-like version for Windows - with engineer and programmer modes, history, support for brackets and advanced mathematical operations."
        run_task(task, "workspaces/calculator", log_manager)


if __name__ == "__main__":
    main()