import ast
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from ..models import ActionResult

def run_coder(
    instruction: str,
    coder_agent: Any,
) -> ActionResult:
    try:
        success = coder_agent.run(instruction)
        if success:
            return ActionResult(success=True, data={"message": "Coder finished successfully. Now verify the work."})
        else:
            return ActionResult(success=False, error="Coder failed or timed out. Check logs.")
    except Exception as e:
        return ActionResult(success=False, error=f"Error running coder: {str(e)}")

def finish_work(
    code_executor: Any,
) -> ActionResult:
    try:
        pack_success, pack_message = code_executor.package_to_exe("app.py")
        if pack_success:
            return ActionResult(success=True, data={"message": "Build successful", "details": pack_message})
        else:
            return ActionResult(success=False, error=f"Build failed: {pack_message}")
    except Exception as e:
        return ActionResult(success=False, error=f"Error finishing work: {str(e)}")

def get_all_symbols(
    file_path: str,
    root_dir: str
) -> ActionResult:
    try:
        full_path = Path(root_dir) / file_path
        if not full_path.exists():
            return ActionResult(success=False, error=f"File not found: {file_path}")
        
        with open(full_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        
        symbols = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(f"{type(node).__name__}: {node.name} (Lines {node.lineno}-{node.end_lineno})")
        
        result = "\n".join(symbols) if symbols else "No symbols found."
        return ActionResult(success=True, data={"symbols": result})
    except Exception as e:
        return ActionResult(success=False, error=f"Error parsing file: {str(e)}")

def open_file(
    file_path: str,
    root_dir: str,
    start_line: int = 1,
    end_line: Optional[int] = None
) -> ActionResult:
    try:
        full_path = Path(root_dir) / file_path
        if not full_path.exists():
            return ActionResult(success=False, error=f"File not found: {file_path}")
        
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if end_line is None:
            end_line = len(lines)
        
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        content = "".join([f"{i+1}: {line}" for i, line in enumerate(lines[start_idx:end_idx], start=start_idx)])
        return ActionResult(success=True, data={"content": content})
    except Exception as e:
        return ActionResult(success=False, error=f"Error reading file: {str(e)}")
