from functools import partial
from typing import Dict, Callable
from .policy import ActionPolicy
from .actions.file import read_file, create_file, edit_file, get_file_tree
from .actions.terminal import run_command
from .actions.python import run_ipython
from .actions.control import finish_task

def build_registry(policy: ActionPolicy) -> Dict[str, Callable]:
    root = str(policy.config.root_dir)
    return {
        "read_file": partial(read_file, root_dir=root, max_bytes=policy.config.max_read_bytes),
        "create_file": partial(create_file, root_dir=root),
        "edit_file": partial(edit_file, root_dir=root),
        "get_file_tree": partial(get_file_tree, root_dir=root),
        "run_command": partial(run_command, root_dir=root, max_output_chars=policy.config.max_output_chars),
        "run_ipython": run_ipython,
        "finish_task": finish_task,
    }