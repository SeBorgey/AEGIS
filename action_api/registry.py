from functools import partial
from typing import Dict, Callable
from .policy import ActionPolicy
from .actions.file import read_file, create_file, edit_file, get_file_tree
from .actions.terminal import run_command
from .actions.python import run_ipython
from .actions.control import finish_task

from .actions.manager import run_coder, finish_work, get_all_symbols, open_file

def build_registry(policy: ActionPolicy) -> Dict[str, Callable]:
    root = str(policy.config.root_dir)
    return {
        "read_file": partial(read_file, root_dir=root, max_bytes=policy.config.max_read_bytes),
        "create_file": partial(create_file, root_dir=root),
        "edit_file": partial(edit_file, root_dir=root),
        "get_file_tree": partial(get_file_tree, root_dir=root),
        "run_command": partial(run_command, root_dir=root, max_output_chars=policy.config.max_output_chars),
        "run_ipython": partial(run_ipython, root_dir=root),
        "finish_task": finish_task,
    }

def build_manager_registry(
    policy: ActionPolicy,
    coder_agent: object,
    code_executor: object
) -> Dict[str, Callable]:
    root = str(policy.config.root_dir)
    return {
        "run_coder": partial(run_coder, coder_agent=coder_agent),
        "finish_work": partial(finish_work, code_executor=code_executor),
        "get_project_tree": partial(get_file_tree, root_dir=root),
        "get_all_symbols": partial(get_all_symbols, root_dir=root),
        "open_file": partial(open_file, root_dir=root),
        "terminal_command": partial(run_command, root_dir=root, max_output_chars=policy.config.max_output_chars),
    }