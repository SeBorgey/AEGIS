import sys
import io
from pathlib import Path
from typing import Optional, Dict, Any
from ..models import ActionResult

_GLOBAL_VARS: Dict[str, Any] = {}

def run_ipython(code: str, reset: bool = False, root_dir: Optional[str] = None) -> ActionResult:
    global _GLOBAL_VARS
    if reset:
        _GLOBAL_VARS.clear()
    
    if root_dir:
        root_path = str(Path(root_dir).resolve())
        if root_path not in sys.path:
            sys.path.insert(0, root_path)

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr
    
    try:
        exec(code, _GLOBAL_VARS)
        success = True
        error = None
    except Exception as e:
        success = False
        error = str(e)
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
    stdout = captured_stdout.getvalue()
    stderr = captured_stderr.getvalue()
    
    data = {
        "stdout": stdout,
        "stderr": stderr,
    }
    
    if success:
        return ActionResult(success=True, data=data)
    else:
        return ActionResult(success=False, data=data, error=error)
