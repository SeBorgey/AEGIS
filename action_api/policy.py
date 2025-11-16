from pydantic import BaseModel
from typing import List, Optional, Union
from pathlib import Path
from shlex import split as shlex_split
from .models import ActionCall

class PolicyConfig(BaseModel):
    root_dir: Path
    allowed_commands: List[str] = []
    command_timeout_sec: int = 10
    max_read_bytes: int = 262144
    max_write_bytes: int = 1048576
    allow_shell: bool = False
    max_output_chars: int = 200000

class ActionPolicy:
    def __init__(self, config: PolicyConfig):
        self.config = config
        self.config.root_dir = Path(self.config.root_dir).expanduser().resolve()

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.config.root_dir / p
        p = p.resolve()
        try:
            p.relative_to(self.config.root_dir)
        except ValueError:
            raise ValueError("Path outside of root_dir")
        return p

    def _validate_command(self, cmd: Union[str, List[str]], shell: Optional[bool]) -> List[str]:
        if isinstance(cmd, str):
            args = shlex_split(cmd)
        else:
            args = cmd
        if not args:
            raise ValueError("Empty command")
        prog = Path(args[0]).name
        if self.config.allowed_commands and prog not in self.config.allowed_commands:
            raise ValueError("Command not allowed")
        if shell and not self.config.allow_shell:
            raise ValueError("Shell execution not allowed")
        return args

    def check(self, call: ActionCall) -> None:
        n = call.name
        p = call.params
        if n == "read_file":
            path = p.get("path")
            if not path:
                raise ValueError("Missing path")
            abs_path = self._resolve_path(path)
            p["path"] = str(abs_path)
            max_bytes = p.get("max_bytes")
            if max_bytes is not None and int(max_bytes) > self.config.max_read_bytes:
                raise ValueError("max_bytes exceeds policy")
        elif n == "create_file":
            path = p.get("path")
            if path is None:
                raise ValueError("Missing path")
            abs_path = self._resolve_path(path)
            p["path"] = str(abs_path)
            content = p.get("content", "")
            size = len(str(content).encode(p.get("encoding", "utf-8")))
            if size > self.config.max_write_bytes:
                raise ValueError("Write exceeds policy")
        elif n == "edit_file":
            path = p.get("path")
            if path is None:
                raise ValueError("Missing path")
            abs_path = self._resolve_path(path)
            p["path"] = str(abs_path)
            if "old" not in p or "new" not in p:
                raise ValueError("Missing old or new")
            new_size = len(str(p.get("new")).encode(p.get("encoding", "utf-8")))
            if new_size > self.config.max_write_bytes:
                raise ValueError("Write exceeds policy")
        elif n == "run_command":
            cmd = p.get("cmd")
            if cmd is None:
                raise ValueError("Missing cmd")
            shell = bool(p.get("shell", False))
            args = self._validate_command(cmd, shell)
            p["cmd"] = args
            timeout = p.get("timeout_sec")
            if timeout is not None and int(timeout) > self.config.command_timeout_sec:
                raise ValueError("Timeout exceeds policy")
            cwd = p.get("cwd")
            if cwd:
                p["cwd"] = str(self._resolve_path(cwd))
        else:
            raise ValueError("Unknown action")