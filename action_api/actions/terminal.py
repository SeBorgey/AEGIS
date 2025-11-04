import subprocess
from pathlib import Path
from typing import Dict, Optional, Union, List
from ..models import ActionResult

def run_command(cmd: Union[str, List[str]], timeout_sec: Optional[int] = None, cwd: Optional[str] = None, shell: bool = False, env: Optional[Dict[str, str]] = None, max_output_chars: Optional[int] = None, root_dir: Optional[str] = None) -> ActionResult:
    args = cmd
    if cwd is None and root_dir:
        cwd = str(Path(root_dir).resolve())
    try:
        r = subprocess.run(args, cwd=cwd, env=env, shell=shell, capture_output=True, text=True, timeout=timeout_sec)
        out = r.stdout or ""
        err = r.stderr or ""
        if max_output_chars is not None:
            out = out[:max_output_chars]
            err = err[:max_output_chars]
        ok = r.returncode == 0
        data = {"return_code": r.returncode, "stdout": out, "stderr": err}
        if ok:
            return ActionResult(success=True, data=data)
        return ActionResult(success=False, data=data, error="Non-zero exit code")
    except Exception as e:
        return ActionResult(success=False, error=str(e))